import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LogoLockup, LogoMark } from "@/components/Logo";

/**
 * Le logo est un dessin, pas une image : ces tests verrouillent ce qui casse
 * en silence dans un SVG assemblé à la main.
 */
describe("logo RushPlay", () => {
  it("expose un nom accessible : le mot reste lisible sans voir le dessin", () => {
    render(<LogoLockup />);
    expect(screen.getByRole("img", { name: "RushPlay" })).toBeInTheDocument();
  });

  it("porte les six éclats et le cercle de l'emblème", () => {
    const { container } = render(<LogoMark />);
    const svg = container.querySelector("svg");

    expect(svg?.querySelectorAll("clipPath path, clipPath circle")).toHaveLength(1);
    // Six éclats découpés, plus le cercle tracé par-dessus.
    expect(svg?.querySelectorAll("g[clip-path] path")).toHaveLength(6);
    expect(svg?.querySelectorAll("circle")).toHaveLength(2);
  });

  it("ne peint aucune couleur en dur : le logo suit le texte qui l'entoure", () => {
    const { container } = render(<LogoLockup />);
    const html = container.innerHTML;

    expect(html).not.toMatch(/fill="#/);
    expect(html).not.toMatch(/stroke="#/);
    expect(html).toContain("currentColor");
  });

  it("« Play » est en retrait, « Rush » ne l'est pas", () => {
    const { container } = render(<LogoLockup />);
    const retrait = container.querySelectorAll('g[opacity="0.55"]');

    expect(retrait).toHaveLength(1);
    // Quatre lettres dans le groupe en retrait : P, l, a, y.
    expect(retrait[0].querySelectorAll("path")).toHaveLength(4);
  });

  it("deux logos sur une page ne partagent pas le même masque", () => {
    const { container } = render(
      <>
        <LogoLockup clipId="un" />
        <LogoMark clipId="deux" />
      </>,
    );

    const ids = [...container.querySelectorAll("clipPath")].map((c) => c.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});
