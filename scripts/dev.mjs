// Lance l'API (FastAPI) et le front (Next.js) ensemble, dans une seule console.
// Chaque ligne de journal est préfixée [api] ou [web] pour qu'on sache qui parle.
//
// Deux choix volontaires :
//   - aucun shell n'est utilisé (ni .cmd, ni `start`) : sinon Windows ouvre des consoles
//     vides à côté, et elles survivent à l'arrêt du script ;
//   - le front reçoit NEXT_PUBLIC_API_URL par l'environnement, qui prime sur .env.local,
//     pour qu'un `npm run dev` parle toujours à l'API locale et jamais à une adresse de
//     déploiement oubliée dans le fichier.
import { spawn, execFileSync } from "node:child_process";
import { createServer } from "node:net";
import { createInterface } from "node:readline";
import { existsSync, readFileSync, writeFileSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const RACINE = dirname(dirname(fileURLToPath(import.meta.url)));
const BACKEND = join(RACINE, "backend");
const FRONTEND = join(RACINE, "frontend");

const HOTE = "127.0.0.1";
const PORT_API = Number(process.env.PORT_API ?? 8000);
const PORT_WEB = Number(process.env.PORT_WEB ?? 3000);
const URL_API = `http://${HOTE}:${PORT_API}`;

// Les mêmes valeurs que backend/dev.cmd : base de démo SQLite, secrets de développement.
// Aucun secret de production ici — la production les reçoit par son hébergeur.
const ENV_API = {
  JWT_SECRET: "test-secret-key-for-pytest-only-32chars",
  CRON_SECRET: "test-cron-secret-key-for-pytest-32chars",
  DATABASE_URL: "sqlite:///./dev.db",
  CORS_ORIGINS: `http://${HOTE}:${PORT_WEB},http://localhost:${PORT_WEB}`,
};

function portLibre(port) {
  return new Promise((resolve) => {
    const s = createServer();
    s.once("error", () => resolve(false));
    s.once("listening", () => s.close(() => resolve(true)));
    s.listen(port, HOTE);
  });
}

// Qui occupe un port ? Sans ça, « le port 3000 est pris » envoie chercher un coupable à la main.
// Un serveur resté debout après une fermeture brutale de la console est le cas courant.
function occupant(port) {
  if (process.platform !== "win32") return null;
  try {
    const sortie = execFileSync("netstat", ["-ano"], { encoding: "utf8" });
    for (const ligne of sortie.split(/\r?\n/)) {
      const m = ligne.match(/^\s*TCP\s+\S+:(\d+)\s+\S+\s+LISTENING\s+(\d+)\s*$/);
      if (m && Number(m[1]) === port) return m[2];
    }
  } catch {
    /* netstat indisponible : tant pis, on reste sur le message générique */
  }
  return null;
}

// Ligne de commande d'un processus, pour ne jamais tuer autre chose que nos propres serveurs.
function ligneDeCommande(pid) {
  if (process.platform !== "win32") return null;
  try {
    return execFileSync(
      "powershell",
      ["-NoProfile", "-Command", `(Get-CimInstance Win32_Process -Filter 'ProcessId=${Number(pid)}').CommandLine`],
      { encoding: "utf8", windowsHide: true },
    ).trim();
  } catch {
    return null;
  }
}

// Un arrêt brutal de la console (fermeture par la croix, arrêt depuis un autre outil) ne laisse
// pas le temps de fermer les enfants : ils restent à écouter et le lancement suivant échoue.
// On garde donc leurs PID sur disque et on nettoie AU DÉMARRAGE — mais seulement si la ligne
// de commande correspond encore à ce qu'on avait lancé, jamais sur la foi du seul numéro,
// que Windows réattribue.
const FICHIER_PIDS = join(RACINE, ".dev-pids.json");
const SIGNATURES = { api: "uvicorn app.main:app", web: `${join("next", "dist", "bin", "next")}` };

function fermer(nom, pid) {
  console.log(`[dev] un serveur ${nom} de la dernière fois tournait encore (PID ${pid}) : je le ferme`);
  try {
    execFileSync("taskkill", ["/pid", String(pid), "/t", "/f"], { stdio: "ignore", windowsHide: true });
  } catch {
    console.error(`[dev] impossible de fermer le PID ${pid} — fais-le à la main : taskkill /pid ${pid} /t /f`);
  }
}

// Est-ce un de NOS serveurs ? Deux preuves acceptées : la signature de la commande, ou le
// simple fait que la commande mentionne ce dépôt. Tout le reste est laissé tranquille.
function estANous(nom, cmd) {
  return Boolean(cmd) && (cmd.includes(SIGNATURES[nom] ?? " ") || cmd.includes(RACINE));
}

function nettoyerRestes() {
  const vus = new Set();
  if (existsSync(FICHIER_PIDS)) {
    let restes = [];
    try {
      restes = JSON.parse(readFileSync(FICHIER_PIDS, "utf8"));
    } catch {
      restes = [];
    }
    for (const { nom, pid } of restes) {
      vus.add(String(pid));
      if (estANous(nom, ligneDeCommande(pid))) fermer(nom, pid);
    }
  }
  // Next lance des ouvriers : c'est parfois un petit-fils, pas l'enfant noté plus haut, qui
  // tient le port. On regarde donc aussi qui écoute réellement sur nos deux ports.
  for (const [nom, port] of [["api", PORT_API], ["web", PORT_WEB]]) {
    const pid = occupant(port);
    if (!pid || vus.has(pid)) continue;
    if (estANous(nom, ligneDeCommande(pid))) fermer(nom, pid);
  }
}

function prefixe(nom, flux) {
  createInterface({ input: flux }).on("line", (ligne) => {
    if (ligne.trim() !== "") console.log(`[${nom}] ${ligne}`);
  });
}

const enfants = [];

function lancer(nom, commande, args, cwd, env) {
  const enfant = spawn(commande, args, {
    cwd,
    env: { ...process.env, ...env },
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true, // pas de fenêtre de console supplémentaire
  });
  prefixe(nom, enfant.stdout);
  prefixe(nom, enfant.stderr);
  enfant.on("error", (e) => {
    console.error(`[${nom}] impossible de démarrer : ${e.message}`);
    arreter(1);
  });
  enfant.on("exit", (code) => {
    console.log(`[${nom}] arrêté (code ${code ?? 0})`);
    arreter(code ?? 0);
  });
  enfants.push(enfant);
  return enfant;
}

let enArret = false;
function arreter(code) {
  if (enArret) return;
  enArret = true;
  for (const e of enfants) {
    if (e.exitCode !== null || e.signalCode !== null) continue;
    // Sur Windows, tuer le processus ne tue pas ses enfants (Next lance des ouvriers) :
    // taskkill /T descend l'arbre entier, sinon le port 3000 reste occupé après un Ctrl+C.
    if (process.platform === "win32") {
      spawn("taskkill", ["/pid", String(e.pid), "/t", "/f"], { stdio: "ignore", windowsHide: true });
    } else {
      e.kill("SIGTERM");
    }
  }
  rmSync(FICHIER_PIDS, { force: true }); // arrêt propre : plus rien à nettoyer au prochain lancement
  setTimeout(() => process.exit(code), 300);
}

process.on("SIGINT", () => arreter(0));   // Ctrl+C
process.on("SIGTERM", () => arreter(0));
process.on("SIGBREAK", () => arreter(0)); // Ctrl+Pause, propre à Windows

// Un .env.local qui désigne une autre API n'est plus appliqué (l'environnement prime),
// mais mieux vaut le dire que de laisser croire à une config active.
const envLocal = join(FRONTEND, ".env.local");
if (existsSync(envLocal)) {
  const ligne = readFileSync(envLocal, "utf8").match(/^NEXT_PUBLIC_API_URL=(.*)$/m);
  const valeur = ligne?.[1].trim();
  if (valeur && valeur !== URL_API) {
    console.log(`[dev] .env.local pointe sur ${valeur} ; ignoré ici, le front parlera à ${URL_API}`);
  }
}

nettoyerRestes();

for (const [nom, port] of [["api", PORT_API], ["web", PORT_WEB]]) {
  if (!(await portLibre(port))) {
    const pid = occupant(port);
    console.error(`[dev] le port ${port} (${nom}) est déjà pris.`);
    if (pid) console.error(`[dev] c'est le processus ${pid} — pour le fermer : taskkill /pid ${pid} /t /f`);
    console.error(`[dev] ou change de port : PORT_${nom.toUpperCase()}=${port + 1} npm run dev`);
    process.exit(1);
  }
}

const nextBin = join(FRONTEND, "node_modules", "next", "dist", "bin", "next");
if (!existsSync(nextBin)) {
  console.error("[dev] dépendances du front absentes. Lance d'abord : cd frontend && npm install");
  process.exit(1);
}

console.log(`[dev] API  ${URL_API}`);
console.log(`[dev] site http://${HOTE}:${PORT_WEB}  (pas localhost : bien plus lent sur ce PC)`);

const api = lancer("api", "python", ["-m", "uvicorn", "app.main:app", "--host", HOTE, "--port", String(PORT_API)], BACKEND, ENV_API);
const web = lancer("web", process.execPath, [nextBin, "dev", "--turbopack", "--hostname", HOTE, "--port", String(PORT_WEB)], FRONTEND, {
  NEXT_PUBLIC_API_URL: URL_API,
});

// Trace pour le prochain lancement, au cas où celui-ci ne se termine pas proprement.
writeFileSync(FICHIER_PIDS, JSON.stringify([{ nom: "api", pid: api.pid }, { nom: "web", pid: web.pid }]));
