# MANUEL — Installer et déployer InSecureDevice sur Qubes OS
> Pour débutant. Chaque commande est expliquée, commande par commande, terme par terme.
> Auteur du manuel : équipe forensique — version 1.0 (air-gapped friendly)

---

## PARTIE A — POURQUOI QUBES ? (contexte, 2 minutes de lecture)

Qubes OS n'est pas un logiciel ordinaire : c'est un **système d'exploitation
composé de plusieurs machines virtuelles (VM)**. Chaque VM est une sorte
d'ordinateur "en carton" qui tourne dans votre vrai ordinateur. Les VMs
peuvent être **isolées** : si l'une est compromise par un malware, les autres
ne le sont pas.

Ce manuel crée **3 machines virtuelles dédiées à notre enquête** :

| VM (nom) | Rôle | Internet ? | Couleur de fenêtre |
|---|---|---|---|
| `insec-app` | Analyse forensique + interface (notre app) | **NON** | rouge |
| `insec-llm` | Le "cerveau IA" local (LM Studio + modèle) | **NON** | bleu |
| `insec-vt` | Consultation VirusTotal (sur le net) | **OUI** (seulement elle) | jaune |

**Règle d'or : jamais Internet dans la VM qui touche le support analysé.**
C'est ça, "air-gapped" : l'outil travaille sans pouvoir envoyer/voler quoi
que ce soit en ligne. La seule VM en contact avec Internet (`insec-vt`) ne
reçoit **jamais** les données du support.

---

## PARTIE B — AVANT L'INSTALLATION : TÉLÉCHARGER ET VÉRIFIER L'ISO

Une ISO = l'image disque à graver pour installer le système. Si elle est
corrompue ou falsifiée, tout le reste est inutile. On vérifie donc **deux
choses** : l'intégrité (le fichier n'est pas abîmé) et l'authenticité
(il a bien été produit par Qubes, pas par un attaquant).

### B1. Télécharger
Rendez-vous sur : **https://www.qubes-os.org/downloads/**
Prenez la dernière **version stable 4.2** et téléchargez les fichiers :
- `Qubes-R4.2.x-x86_64.iso`            → l'image installateur
- `Qubes-R4.2.x-x86_64.iso.sha256`     → l'empreinte numérique officielle
- `Qubes-R4.2.x-x86_64.iso.asc`        → la signature PGP officielle

### B2. Vérifier l'intégrité (l'empreinte SHA-256)
Une empreinte SHA-256 est une "trace" cryptographique du fichier : si le
fichier change ne serait-ce que d'un octet, l'empreinte change totalement.

Sous **Linux** (votre machine actuelle) :
```bash
sha256sum -c Qubes-R4.2.x-x86_64.iso.sha256
```
Explication des termes :
- `sha256sum` : l'outil qui calcule l'empreinte.
- `-c` : "check" = vérifie en comparant avec le contenu du fichier `.sha256`.
- `Qubes-...iso.sha256` : le fichier qui contient l'empreinte **attendue**.
Résultat attendu : `OK`. Tout autre message = ISO abîmée → **recommencez le téléchargement**, n'allez pas plus loin.

Sous **Windows (PowerShell)** :
```powershell
Get-FileHash Qubes-R4.2.x-x86_64.iso -Algorithm SHA256
```
- `Get-FileHash` : calcule l'empreinte.
- `-Algorithm SHA256` : on utilise la méthode SHA-256.
Comparez **à l'œil** la valeur affichée avec celle du fichier `.sha256`.
Identiques = OK.

### B3. Vérifier l'authenticité (signature PGP)
La signature PGP prouve que **Qubes OS a bien signé ce fichier**.
Importer la clé publique officielle puis vérifier :

```bash
gpg --keyserver hkps://keys.gnupg.net --recv-keys 427F11FD0FAA4B080123F01FCDDF29FD
gpg --verify Qubes-R4.2.x-x86_64.iso.asc Qubes-R4.2.x-x86_64.iso
```
Explication des termes :
- `gpg` : le logiciel de chiffrement/signature (GnuPG).
- `--keyserver hkps://keys.gnupg.net` : où aller chercher la clé (le serveur de clés).
- `--recv-keys 427F...FD` : "receive" = télécharge la clé identifiée par ce numéro
  (l'empreinte longue de la clé officielle de Qubes).
- `--verify` : on demande à `gpg` de contrôler la signature.
- On lui donne deux fichiers : la signature (`.asc`) et l'image (`.iso`).
Résultat attendu : une ligne `Good signature from "Qubes OS..."`.
Si vous voyez `BAD signature` → **arrêtez-vous tout de suite**, le fichier est douteux.

> 🛡️ **Règle forensique** : ne jamais installer depuis un fichier dont la
> signature ne passe pas. C'est NON NÉGOCIABLE.

---

## PARTIE C — CRÉER LA CLÉ USB D'INSTALLATION

Il faut une clé USB d'au moins **8 Go**. Cette clé doit être **entièrement
effacée** par l'installation.

Sous **Windows**, utilisez **Rufus** (outil gratuit) :
`https://rufus.ie/`
1. Clé USB insérée → dans Rufus : "Périphérique" = votre clé.
2. "Sélection de boot" = votre fichier `.iso`.
3. Cliquez **DÉMARRER** → mode **ISO** (ou DD si proposé), OK, OK.
La clé est prête.

> ⚠️ La clé utilisée pour installer sera VIDÉE. Utilisez-en une sans
> documents importants, ou sauvegardez-la d'abord.

---

## PARTIE D — INSTALLER QUBES OS

Démarrer sur la clé = au démarrage de l'ordinateur, presser la touche
indiquant le "menu de démarrage" (souvent `F12`, ou `Échap`, ou `F9` selon
le fabricant) et choisir la clé USB.

Suivez l'assistant d'installation :
1. **Langue** → Français.
2. **Clavier** → Français (AZERTY).
3. **Disque + chiffrement** : choisissez l'option **chiffrer le disque**
   (LUKS). Cela protège vos données si la machine est volée. Cochez la case
   et définissez une **passphrase solide** (longue, avec majuscules,
   chiffres, symboles). Notez-la dans un endroit sûr et **secret**.
   - *Qu'est-ce que LUKS ?* = système de chiffrement de disque : sans la
     passphrase, personne ne peut lire les données, même en démontant le disque.
4. **Région / fuseau horaire** → pays concerné.
5. **Compte utilisateur** : c'est le compte de base (sera dans *dom0*).
   Créez un nom d'utilisateur et un mot de passe.
6. Laissez les options par défaut (templates Debian et Fedora proposés).
7. **Installer**. L'installation prend ~10–20 minutes.
8. Redémarrez, retirez la clé USB, entrez votre passphrase de chiffrement
   au boot (celle de LUKS), puis votre compte et mot de passe.

---

## PARTIE E — PREMIÈRE CONNEXION : DÉCOUVRIR dom0 ET LES TERMES

Quand vous êtes sur Qubes, vous voyez des **fenêtres avec des bordures de
couleur**. La fenêtre depuis laquelle on administre tout est **dom0** :
c'est une fenêtre au fond (noire ou grise) appelée, dans le menu Qubes,
*Qubes Manager* / terminal dom0.

Vocabulaire indispensable (à relire avant chaque commande) :
- **dom0** : la VM maîtresse. On **n'y installe jamais de logiciel**, on ne
  l'utilise que pour **gérer les autres VMs** et les commandes d'administration.
- **AppVM** : une VM de travail, dans laquelle on fait nos analyses.
  Créée à partir d'un **TemplateVM**. Elle est **volatile** : si on l'efface,
  elle se recrée propre au prochain redémarrage (tout ce qui n'est PAS dans
  son dossier `home` et les `private` est perdu volontairement).
- **TemplateVM** : le "moule". C'est lui qui porte le système et les logiciels
  installés. Changer le template change toutes les VMs qui l'utilisent.
- **NetVM** : la VM qui fournit le réseau à une autre.
- **qvm-*** : le préfixe de toutes les commandes d'administration Qubes.
- **qrexec** : le mécanisme interne qui permet à une VM de demander un
  service à une autre (par ex. copier un fichier).

Pour **ouvrir un terminal dom0** : clic-droit sur le bureau → *Terminal* (dom0).
Toutes les commandes qui suivent s'effectuent **dans ce terminal dom0**
sauf si précisé "dans la VM".

---

## PARTIE F — METTRE À JOUR LE SYSTÈME (obligatoire, avant tout le reste)

Dans dom0 :
```bash
sudo qubes-dom0-update
```
Explication :
- `sudo` : "super user do" = exécute la commande en mode administrateur
  (les droits d'administration).
- `qubes-dom0-update` : l'outil officiel pour mettre à jour dom0 lui-même
  (noyau, drivers, outils). Équivalent du "Windows Update" de Qubes.
Tapez votre mot de passe dom0 quand il le demande. Attendez la fin.

Ensuite, mettez à jour les modèles (templates) :
```bash
sudo qubes-update-gui
```
- `qubes-update-gui` : ouvre une fenêtre graphique listant tous les templates.
Cochez **tous** les templates présents, cliquez **Apply / Appliquer**, puis
**Update / Mettre à jour**. Attendez la fin (plusieurs minutes).

> 🛡️ Toujours commencer par les mises à jour avant toute création de VM.

---

## PARTIE G — CRÉER NOS VMs (dans dom0)

On va créer, dans l'ordre :
1. un **template dédié** `insec-tpl`
2. trois **AppVM** : `insec-app`, `insec-llm`, `insec-vt`

### G1. Vérifier quel template de base existe
```bash
qvm-template list
```
- `qvm-template` : outil de gestion des templates (le "moule").
- `list` : affiche ceux disponibles.
Attendu : `debian-12-xf4` (ou `debian-12`), `fedora-40-xf4`...
Notez le nom exact de celui en Debian.

### G2. Créer notre moule dédié (copie d'un template)
```bash
qvm-clone debian-12-xf4 insec-tpl
```
- `qvm-clone` : "clone" = duplique un template.
- `debian-12-xf4` : le template à copier (source).
- `insec-tpl` : le nom que reçoit la copie (notre moule de travail).
Résultat : une copie indépendante du moule, qu'on pourra modifier sans
toucher à l'original.

### G3. Créer nos trois AppVM
```bash
qvm-create --template insec-tpl --label red insec-app
qvm-create --template insec-tpl --label blue insec-llm
qvm-create --template insec-tpl --label yellow insec-vt
```
Explication (pour la première !) :
- `qvm-create` : crée une nouvelle VM.
- `--template insec-tpl` : cette VM est **faite à partir du moule** `insec-tpl`
  (donc elle suit nos modifications du moule).
- `--label red` : couleur de la bordure de fenêtre. Rouge = zone sensible
  sans réseau. (Les couleurs sont une *convention de sécurité visuelle*.)
- `insec-app` : le nom de la VM.
Refaites la même commande pour `insec-llm` (bleu) et `insec-vt` (jaune).

### G4. Gérer le réseau de chaque VM (très important)
C'est ici qu'on installe notre "air-gapped".
```bash
qvm-prefs -s insec-app netvm none
qvm-prefs -s insec-llm netvm none
qvm-prefs -s insec-vt  netvm sys-net
```
Explication (première ligne) :
- `qvm-prefs` : lit/modifie les paramètres d'une VM.
- `-s` : "set" = on définit une valeur.
- `insec-app` : la VM concernée.
- `netvm` : le paramètre "quelle VM fournit Internet ?".
- `none` : **aucune** → `insec-app` n'a **aucun accès réseau**. C'est notre
  isolation ceinture et bretelles.
Autres lignes : pareil pour `insec-llm` (pas de réseau). ET `insec-vt`
avec `sys-net` (la VM qui a accès à Internet) = **seule** celle-là a le réseau.

> 🛡️ Résultat : `insec-app` et `insec-llm` ne peuvent ni envoyer ni recevoir
> de données sur le net. Parfait pour un environ air-gapped.

### G5. Éventuellement, donner plus de ressources à la VM IA
```bash
qvm-prefs -s insec-llm memory 4096
qvm-prefs -s insec-llm vcpus 2
```
- `memory 4096` : 4096 Mo (4 Go) de RAM pour `insec-llm` (un modèle IA est gourmand).
- `vcpus 2` : 2 cœurs de processeur. (Ajustez selon votre machine ; si vous
  avez beaucoup de RAM, mettez `memory 8192` pour le modèle IA.)

---

## PARTIE H — DÉMARRER LES VMs POUR LA PREMIÈRE FOIS

```bash
qvm-start insec-app
```
- `qvm-start` : démarre la VM.
- `insec-app` : laquelle.
Refaites pour `insec-llm` et `insec-vt`. Une fenêtre de chaque couleur doit
apparaître (rouge, bleue, jaune).

Pour ouvrir un terminal **dans** une VM, depuis dom0 :
```bash
qvm-run insec-app xterm
```
- `qvm-run` : exécute une commande dans une autre VM.
- `insec-app` : laquelle.
- `xterm` : la commande à lancer = ouvrir un terminal.

---

## PARTIE I — INSTALLER L'APPLICATION DANS insec-app

### I1. Ouvrir un terminal dans insec-app
Faites : `qvm-run insec-app xterm` (ou cliquez sur la fenêtre rouge puis
menu Applications → Terminal).

### I2. Mettre à jour les paquets et installer Python
```bash
sudo apt update
```
- `sudo` : administrateur.
- `apt` : le gestionnaire de paquets Debian (installe/désinstalle les logiciels).
- `update` : met à jour la liste des logiciels disponibles.
```bash
sudo apt install -y python3-venv python3-pip git
```
- `install` : installe des logiciels.
- `-y` : "yes" = ne pas demander confirmation à chaque paquet.
- `python3-venv` : utile pour créer un environnement Python isolé.
- `python3-pip` : l'installeur de paquets Python.
- `git` : pour récupérer le code source.

### I3. Copier le dossier de l'application dans insec-app
Depuis l'ordinateur Windows (ou une autre source), copiez le dossier
`InSecureDevice` vers insec-app. Le plus propre en air-gapped : via une
clé USB passant par `sys-usb`, ou via `qvm-copy` (voir Partie K).

Si le dossier s'appelle `InSecureDevice` et qu'il est disponible :
```bash
mv InSecureDevice ~/app
```
- `mv` : déplace (et peut renommer).
- `InSecureDevice` : le nom actuel.
- `~/app` : le nouveau nom (`~` = votre dossier personnel, `app` le nouveau nom).
Ou plus simple : `cd InSecureDevice` pour y entrer sans renommer.

### I4. Créer l'environnement Python et installer les dépendances
```bash
cd ~/app
python3 -m venv .venv
```
- `cd` : "change directory" = on se place dans le dossier.
- `~/app` : notre dossier app.
- `python3 -m venv .venv` : demande au Python de créer un environnement
  virtuel nommé `.venv` : un espace isolé pour nos bibliothèques, pour ne pas
  polluer le système.
```bash
source .venv/bin/activate
```
- `source` : charge le fichier.
- `.venv/bin/activate` : rend `.venv` actif (désormais, `python` =
  celui de `.venv`).
```bash
pip install -r requirements.txt
```
- `pip` : l'installeur Python.
- `install` : installe.
- `-r requirements.txt` : "read from" le fichier `requirements.txt` qui liste
  les paquets nécessaires (PySide6 pour l'interface, capstone pour le
  désassemblage...). `pip` les installe tous.

---

## PARTIE J — RÉGLER LA CONFIGURATION (les variables d'environnement)

Notre application lit sa configuration par **variables d'environnement** :
ce sont des zone-repères que le système met à disposition des programmes.

Dans le terminal de insec-app :
```bash
echo 'export AI_BACKEND="openai"' >> ~/.bashrc
echo 'export AI_MODEL="qwen/qwen2.5-coder-14b"' >> ~/.bashrc
echo 'export AI_BASE_URL="http://10.8.0.2:1234"' >> ~/.bashrc
```
Explication (première) :
- `echo` : affiche du texte.
- `'export AI_BACKEND="openai"'` : le texte = on définit une variable
  d'environnement nommée AI_BACKEND avec la valeur openai.
- `>` : redirige (écrit) vers...
- `>` `>>` : **ajoute** à la fin du fichier (sans écraser).
- `~/.bashrc` : le fichier de configuration de ton terminal bash, chargé à
  chaque ouverture.
- `export` : rend la variable visible aux programmes qu'on lance ensuite.
Résultat : à chaque ouverture de terminal, ces 3 variables seront définies.
- `AI_BACKEND=openai` : on dit "je me connecte à une IA type OpenAI".
- `AI_MODEL=qwen/qwen2.5-coder-14b` : le modèle (un très bon modèle "coder"
  de 14 milliards de paramètres).
- `AI_BASE_URL=http://10.8.0.2:1234` : l'adresse où se trouve l'IA locale
  (sera à adapter à votre réseau Qubes privé entre insec-llm et insec-app).

> ⚠️ La valeur `10.8.0.2` est un **exemple**. Mettez la **vraie** adresse IP
> de insec-llm dans votre réseau Qubes interne (voir Partie L).

Relancez votre terminal (ou `source ~/.bashrc`) pour appliquer.
Pour les tests sans IA (recommandé au premier lancement) :
```bash
export AI_BACKEND="dev"
```
→ l'application utilise un "faux cerveau" local, pour vérifier que le
pipeline tourne sans besoin du modèle. Puis remettez `openai` quand le LLM
est prêt.

---

## PARTIE K — INSÉRER UN SUPPORT À ANALYSER (clé USB, disque)

C'est le cœur du travail de l'enquêteur : analyser une clé USB trouvée
sur les lieux. Pour éviter qu'un malware dessus infecte la VM : on branche
le support **lecture seule** dans notre VM d'analyse.

Dans **dom0**, listez les supports branchés :
```bash
qvm-block list
```
- `qvm-block` : l'outil de gestion des blocs (disques/clés).
- `list` : affiche les disques détectés (ceux de sys-usb / sys-net).
Exemple de sortie :
```
sys-usb:sda personal:... (usb-X)
```
La colonne de gauche donne le nom à utiliser, par ex. `sys-usb:sda`.

Ensuite, **attachez** ce support dans notre VM d'analyse (lecture seule) :
```bash
qvm-block attach insec-app sys-usb:sda --option ro
```
Explication :
- `qvm-block attach` : "attacher" = donner ce disque à une VM.
- `insec-app` : la VM qui va le recevoir (notre VM d'analyse).
- `sys-usb:sda` : le support (venant de la VM sys-usb, disque sda).
- `--option ro` : `ro` = "read only" = **lecture seule**. Le support ne peut
  pas être écrit : protection absolue contre les modifications accidentelles (et
  preuve forensique intacte).
Depuis insec-app, le support apparaît alors comme `/dev/xvdi` (nom d'exemple) ;
l'application `insecured` sait le monter (elle s'attend à le trouver dans un
dossier de montage ; vous pouvez le monter manuellement :
```bash
mkdir -p ~/mnt && sudo mount /dev/xvdi ~/mnt
```
- `mkdir -p ~/mnt` : crée le dossier `mnt` (`-p` = crée aussi les parents s'il manque).
- `mount /dev/xvdi ~/mnt` : rend le contenu du disque accessible dans `mnt`).

---

## PARTIE L — LE CERVEAU IA DANS insec-llm (LM Studio)

Les modèles IA qu'on utilise (ex. Qwen2.5-coder) s'exécutent avec un serveur
local type **LM Studio** ou **Ollama**, dans `insec-llm` (qui n'a pas Internet,
donc les modèles y ont été déposés hors-ligne).

1. Dans `insec-llm`, installez LM Studio (via une clé/paquet déposé hors-ligne)
   et déposez-y le fichier du modèle `qwen2.5-coder-14b`.
2. Lancez le **serveur** :
   ```bash
   lm-studio serve --host 0.0.0.0 --port 1234
   ```
   - `lm-studio serve` : lance le serveur d'IA de LM Studio.
   - `--host 0.0.0.0` : écoute sur toutes les interfaces réseau (pour être
     joignable depuis insec-app).
   - `--port 1234` : le port réseau (même que AI_BASE_URL !).
3. Reliez insec-app → insec-llm par le réseau Qubes privé (même NetVM, ou
   directement via le reseau local si configuré). Concrètement, pour que
   insec-app atteigne insec-llm, les deux doivent être sur un même réseau
   privé (par ex. NetVM `sys-net` partagé inter-seulement, OU configurer
   `insec-llm` et `insec-app` avec un réseau local Qubes : les deux sur le
   même `netvm`). Adaptez `AI_BASE_URL` avec l'adresse IP réelle de insec-llm
   obtenue via :
   ```bash
   qvm-run insec-llm "ip addr show"
   ```
   Repérez l'adresse IPv4 (par ex. `10.8.0.2/24`) → mettez-la dans
   `AI_BASE_URL=http://<cette-adresse>:1234`.

> 💡 En air-gapped strict, insec-app et insec-llm peuvent communiquer en LAN
> interne Qubes sans Internet — c'est exactement ce qu'on veut.

---

## PARTIE M — LANCER L'ANALYSE

Dans insec-app (terminal actif) :
```bash
cd ~/app
source .venv/bin/activate
python -m insecured
```
- `python -m insecured` : lance le module Python `insecured` (notre application :
  elle ouvre l'interface graphique PySide6).
L'interface s'ouvre : créez un **nouveau cas**, pointez le dossier
monté (Partie K), lancez la pipeline (bouton). Vous verrez défiler :
`mount → inventory → hashing → metadata → anomalies → vt_check →
ai_analysis → report`.

Test rapide sans interface (ligne de commande, pratique pour vérifier) :
```bash
python -m insecured pipeline <dossier-à-analyser>
```
- `pipeline` : sous-commande qui exécute toute l'analyse.
- `<dossier-à-analyser>` : le dossier monté (ex. `~/mnt`).
Un **rapport** est alors généré et **écrit dans un fichier** dans le dossier
`RAPPORTS/` situé à côté / dans le cas (cf. contrôle dans l'app).

---

## PARTIE N — DÉPANNAGE RAPIDE

| Problème | Cause probable & solution |
|---|---|
| `qvm-block list` ne montre rien | Rien branché dans sys-usb, ou support non reconnu. Réinsérez la clé, répétez. |
| `insec-app` n'a pas de réseau | Normal pour notre design ! insec-app a `netvm none`. |
| L'app ne "parle" pas à l'IA | Vérifiez `AI_BASE_URL` (l'IP réelle de insec-llm), que le serveur tourne (`lm-studio serve`), et que les deux VMs se voient (même réseau Qubes). |
| Le rapport met >30 s / "IA rédige le rapport" | C'est le garde-fou prévu : au-delà de 30 s, l'app écrit un rapport **sans IA** (fallback) et le fichier est quand même créé. Pas un bug. |
| "Attachment" erreur | Vérifiez le nom exact dans `qvm-block list` ; réessayez `--option ro`. |

---

## PARTIE O — VÉRIFICATIONS FINALES (checklist)

- [ ] ISO vérifiée : SHA-256 `OK` + signature PGP `Good signature`
- [ ] dom0 et templates mis à jour
- [ ] 3 VMs créées (app/llm/vt) avec templates
- [ ] `insec-app` = `netvm none` (air-gapped) ✔
- [ ] `insec-llm` = `netvm none` ✔
- [ ] Application installée : venv + requirements + config
- [ ] Support branché en **lecture seule** (`qvm-block attach --option ro`)
- [ ] Rapport généré **et fichier créé** (dossier RAPPORTS)
- [ ] (Optionnel) VirusTotal configuré uniquement dans `insec-vt`

---

> Ce manuel accompagne le code du dépôt `InSecureDevice` et son module d'analyse
> `insecured`. En cas de doute sur une commande, relisez la partie concernée —
> chaque terme est expliqué. Bonne enquête. 🕵️
