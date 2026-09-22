FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
ENV PYTHONUNBUFFERED=1 ENV=production
EXPOSE 8000
# Un utilisateur sans privilège : le conteneur tournait en root (audit du 22/09/2026).
RUN useradd --system --no-create-home --uid 10001 rushplay && chown -R rushplay:rushplay /app
USER rushplay

# --proxy-headers / --forwarded-allow-ips : derrière Traefik (Coolify), sans ces options tous les
# visiteurs ont l'IP du proxy et la limitation de débit plafonnait les inscriptions à 5 par heure
# POUR TOUT LE SITE. Le conteneur n'est joignable que par le proxy : on lui fait confiance.
# --no-server-header : ne pas annoncer « uvicorn ».
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*' --no-server-header"]
