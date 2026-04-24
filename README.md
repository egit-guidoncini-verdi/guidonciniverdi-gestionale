# Gestionale Guidoncini Verdi

<img title="" src="./static/gv.jpg" alt="" width="100" data-align="center">

Gestionale utilizzato per validare le iscrizioni al percorso Guidoncini Verdi di:

[AGESCI Piemonte](https://piemonte.agesci.it/)

[AGESCI Valle d'Aosta](https://valdaosta.agesci.it/)

[AGESCI Puglia](https://puglia.agesci.it/)

[AGESCI Sardegna](https://sardegna.agesci.it/)

La validazione iscrizioni genera delle richieste alle API di [guidonciniverdi.it](https://guidonciniverdi.it/) per la creazione dell'account utente e delle pagine del Diario di Bordo.

<img title="" src="./static/pag_iscrizioni.png" alt="" width="554" data-align="center">

Il gestionale si occupa inoltre dell'invio di mail a ragazzi e capi.

Generazione file excel delle iscrizioni per tutti i livelli di utenza (nei limiti della stessa).

### Deploy
Docker compose: 
```yaml
services:
  gestionale:
    image: ghcr.io/egit-guidoncini-verdi/guidonciniverdi-gestionale:latest
    restart: unless-stopped
    environment:
      DB_TYPE: mariadb
      DB_USER: app_user
      DB_PASSWORD: app_password
      DB_HOST: db
      DB_PORT: 3306
      DB_NAME: app_db
      SECRET_KEY: secret_key
      WORDPRESS_URL: "https://dominio.it/wp-json/wp/v2"
      WORDPRESS_USER: utente
      WORDPRESS_PASSWORD: "WORDPRESS_PASSWORD"
      TELEGRAM_TOKEN: "TELEGRAM_TOKEN"
    depends_on:
      - db

  gestionale-daemon:
    image: ghcr.io/egit-guidoncini-verdi/guidonciniverdi-gestionale-daemon:latest
    restart: unless-stopped
    environment:
      MAIL_USERNAME: "noreply@dominio.it"
      MAIL_HOST: smtp
      MAIL_PORT: 587
      DB_TYPE: mariadb
      DB_USER: app_user
      DB_PASSWORD: app_password
      DB_HOST: db
      DB_PORT: 3306
      DB_NAME: app_db
      URL_NOTIFICHE: "http://gestionale:8000/notifica"
      API_KEY: "KEY"
    depends_on:
      - db
      - smtp

  db:
    image: mariadb:11.4
    container_name: mariadb
    restart: unless-stopped
    environment:
      MARIADB_ROOT_PASSWORD: rootpassword
      MARIADB_DATABASE: app_db
      MARIADB_USER: app_user
      MARIADB_PASSWORD: app_password
      TZ: Europe/Rome
    volumes:
      - mariadb-data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mariadb-admin", "ping", "-h", "localhost", "-uroot", "-prootpassword"]
      interval: 5s
      timeout: 3s
      retries: 5

  smtp:
    image: boky/postfix
    container_name: smtp_relay
    environment:
      ALLOWED_SENDER_DOMAINS: "dominio.it"
      RELAYHOST: "[authsmtp.securemail.pro]:587"
      RELAYHOST_USERNAME: "noreply@dominio.it"
      RELAYHOST_PASSWORD: "PASSWORD"
    depends_on:
      - gestionale

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "5000:80"
    volumes:
      - nginx:/etc/nginx
    depends_on:
      - gestionale

volumes:
  mariadb-data:
  nginx:
```

Per il primo setup è necessario eseguire i seguenti comandi sul container "gestionale":
```bash
flask db upgrade #Aggiorna lo schema del DB
flask init_db #Crea l'utente admin e inizializza con dati default
```
Ad ogni aggiornamento di versione è sufficiente:
```bash
flask db upgrade #Aggiorna lo schema del DB
```
Comandi utili:
```bash
flask crea_regione piemonte #Crea la regione
```
### Scelte implementative

Gestione del backend tramite Flask ([Documentazione qui](https://flask.palletsprojects.com/)).

Come database è stato scelto MariaDB ([Documentazione qui](https://mariadb.org/)) per la sua leggerezza e semplicità, l'interazione con il database è gestita tramite l'ORM SQLAlchemy ([Documentazione qui](https://www.sqlalchemy.org/)).

### Livelli di utente

Sono presenti quattro livelli di utente.

| Livello       | Permessi                                                                                                                                                                                                                                                                                                                                     |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Admin         | Può fare tutto, inoltre vede i dati grezzi di ogni risposta                                                                                                                                                                                                                                                                                  |
| IABR          | Può vedere e autorizzare le squadriglie di tutta la regione, eliminare eventuali risposte al form erronee, modificare dettagli delle iscrizioni, avviare il percorso a inizio anno e concludere l'anno eliminando tutti gli account wordpress (maggiori dettagli quando implementato) e mandare mail a squadriglie iscritte e/o capi reparto |
| Pattuglia E/G | Può vedere e autorizzare le squadriglie di tutta la regione                                                                                                                                                                                                                                                                                  |
| IABZ          | Può vedere e autorizzare le squadriglie della sua zona                                                                                                                                                                                                                                                                                       |

### Future

- Reset password degli utenti wordpress

- Possibilità di creare pagine extra su wordpress

- Sistema di reset a fine anno
