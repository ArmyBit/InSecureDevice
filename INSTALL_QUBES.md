# InSecureDevice — Manuel d'installation sur Qubes OS (air-gapped)

> **Public** : investigateur forensique, aucun prérequis Qubes exigé.
> Chaque commande est décomposée **mot à mot**. Tapez-là dans le terminal
> **dom0** (sauf indication contraire) — c'est le terminal que vous avez en
> arrivant sur la session, reconnaissable car sa fenêtre s'appelle `dom0`.
> Lignes commençant par `#` = commentaires (à ne pas taper).

---

## Phase 0 — Comprendre les briques Qubes (20 min, indispensable)

Qubes n'est pas un logiciel, c'est un **système de fenêtres colorées** :
chaque programme tourne dans une **machine virtuelle (VM)** séparée, avec sa
propre couleur de bordure. Si une VM est compromise, les autres restent
intactes.

Vocabulaire minimal (vous en croiserez partout) :

| Terme | Sens simple |
|---|---|
| **dom0** | Votre "pilote de bord". Il gère toutes les VMs. On **n'y installe rien**, on n'y crée que des machines et on y tape les commandes système. |
| **TemplateVM (template)** | Le "moule". Contient le système + les logiciels installés ({virtual}.modifiable). **Jamais lancée telle quelle** : elle sert à dérouler des copies. |
| **AppVM (AppVM = machine application)** | Une "copie" du template, **lisible seulement**. C'est LÀ que vous travaillez. Reboot = état propre. |
| **NetVM** | La VM qui fournit Internet à d'autres. `sys-net` = le routeur réseau. |
| **sys-usb** | La VM qui gère les **clés USB** (porte-USB). Très important pour nous : notre support d'enquête y sera branché. |
| **qrexec / qvm-*\*** | Les outils désignés **dom0→VM** (`qvm-create`, `qvm-prefs`...) et **VM→VM** (`qvm-copy`). |
| **vérification PGP** | Signer/vérifier qu'un fichier est authentique (cryptographie à clés). |

**Notre architecture cible (3 VM dédiées, cf. WORKFLOW.md) :**

```
                     +-----------------+       +------------------+
                     |   insec-app     |       |   insec-llm      |
                     |  analyse + UI   |       |  LM Studio (LLM) |
                     |  netvm = none   |       |  netvm = none    |
                     +--------+--------+       +--------+---------+
                              |  qrexec (local uniquement)
+--------+                    |                    +------------------+
| sys-usb|==support USB==>    |                    |   insec-vt       |
+--------+   (qvm-block)      |                    |  VirusTotal      |
                              |                    |  netvm = sys-net |
                              v                    +------------------+
                     +-----------------+
                     |   sys-net       |  <-- Internet (INAUDIBLE)
                     +-----------------+
```

- **insec-app** : le pipeline forensique (notre app). **Aucun réseau** (`netvm=none`).
  C'est la règle d'or air-gapped : l'analyse ne contacte jamais l'extérieur.
- **insec-llm** : votre modèle IA (LM Studio) tourne ICI, en local, air-gapped.
- **insec-vt** : SEULE VM connectée à Internet (via sys-net), utilisée pour les
  requêtes VirusTotal. On ne lui envoie JAMAIS le contenu brut des supports.

---

## Phase 1 — Télécharger et VÉRIFIER l'image (fatale si sautée)

Un adversary peut truquer un ISO. La **vérification d'intégrité** est
non négociable. Étape à faire sur une machine **non sensible** (votre PC).

1.1 — Télécharger au bon endroit
```
https://qubes-os.org/downloads/
```
Prenez pour 2026 : **Qubes 4.2.x** (Xen 4.17, templates intégrés).
Fichiers à récupérer :
- `Qubes-R4.2.x-x86_64.iso`
- `Qubes-R4.2.x-x86_64.iso.asc`   (signature PGP)
- `Qubes-R4.2.x-x86_64.iso.sha256` (empreinte)

1.2 — Vérifier l'empreinte (SHA-256)
Sous Linux :
```bash
sha256sum -c Qubes-R4.2.x-x86_64.iso.sha256
```
Sous Windows (powershell) :
```powershell
Get-FileHash Qubes-R4.2.x-x86_64.iso -Algorithm SHA256
```
le résultat doit être **identique** à celui listé dans `*.sha256`. Sinon :
**jetez l'ISO**, il est corrompu.

1.3 — Vérifier la signature PGP (authenticité)
Clé officielle des developers Qubes : **`427F 11FD 0FAA 4B08 0123 F01F CDDF 29FD 0000 0000`**
(notez : "427F...0000" est un exemple de format, prenez celle affichée sur
le site officiel — regardez `Verify` sur qubes-os.org).
```bash
gpg --keyserver hkps://keys.gnupg.net --recv-keys 427F11FD0FAA4B080123F01FCDDF29FD00000000
gpg --verify Qubes-R4.2.x-x86_64.iso.asc Qubes-R4.2.x-x86_64.iso
```
Résultat attendu : `Good signature from "Qubes OS Release X"`.
Pas de "Good signature" ? → recommencez ou abandonnez.

---

## Phase 2 — Installer Qubes sur la machine (boot USB)

2.1 — Graver l'ISO sur une clé USB (≥ 8 Go)
Sous Windows, outil simple : **Rufus**, mode **DD Image**. La clé devient
le support de démarrage. Vérifiez dans le BIOS que vous pouvez démarrer
depuis une clé USB (souvent touche `F12` ou `Esc` au démarrage).

2.2 — Installer
1. Démarrer sur la clé → menu **Install Qubes OS**.
2. **Langue**, **clavier** : français.
3. Partitionnement : choisissez **"Encryption" (LUKS, chiffrement du disque)**
   et définissez une **passphrase solide**. C'est notre protection si l'ordinateur
   est volé pendant l'enquête. (LUKS = "Linux Unified Key Setup" : le disque est
   chiffré, ne se lit qu'avec le mot de passe.)
4. Sélecteur d'environnement : gardez les options par défaut.
5. Démarrage => voici votre **dom0**. Première connexion en `user`.

---

## Phase 3 — Premières commandes dom0 (mise à jour + premiers pas)

3.1 — Mettre à jour les templates et sys-* (CRITIQUE, à faire avant tout)
Dans **dom0** (votre bon vieux terminal) tapez :
```bash
sudo qubes-dom0-update
```
- `sudo` : "super user do", exécute en mode administrateur.
- `qubes-dom0-update` : met à jour le système dom0 lui-même (noyau, Xen...).

Puis mettez à jour les templates et sys-* :
```bash
sudo qubes-update-gui
```
Lance un assistant graphique : sélectionnez toutes les templates
(`debian-12-xf4`, `fedora-4x`) et **Apply**.

3.2 — Architecture de test rapide (option) : si vous voulez juste "voir" Qubes.
```bash
qvm-start sys-firewall
qvm-start --skip-if-running debian-12-xf4
```
Expliquons chaque mot de `qvm-start`:
- `qvm-start` : commande dom0 "démarrer une VM"
- `sys-firewall` : la VM pare-feu par défaut (elle est généralement déjà démarrée)
- `--skip-if-running` : ne pas planter si elle tourne déjà
- `debian-12-xf4` : le template de bureau Debian fourni

---

## Phase 4 — Créer notre projet : les 3 VMs forensiques

Rappel d'objectif : **insec-app** (analyse, air-gapped), **insec-llm** (LLM),
**insec-vt** (VirusTotal, seul connecté).

> ⚠️ Tout ceci se tape dans **dom0**.

4.1 — Vérifier les templates disponibles
```bash
qvm-template list
```
Cherchez une ligne `debian-12-xf4`. Si absente, installez-la d'abord
(la suite créer notre appli à partir de ce moule).

4.2 — Cloner un "moule dédié" (bonne pratique : ne jamais installer nos
outils dans le template de base Debian, mais dans un template personnel).
```bash
qvm-clone debian-12-xf4 insec-tpl
```
- `qvm-clone` : duplique.
- `debian-12-xf4` : le moule source.
- `insec-tpl` : nom du nouveau template (moule).

4.3 — Créer les 3 VMs d'exécution depuis ce moule
```bash
qvm-create --template insec-tpl --label red insec-app
qvm-create --template insec-tpl --label blue insec-llm
qvm-create --template insec-tpl --label yellow insec-vt
```
- `qvm-create` : crée une VM.
- `--template insec-tpl` : elle est faite à partir du moule `insec-tpl`.
- `--label red/blue/yellow` : couleur de la bordure (utile pour repérer).
- les trois noms : nos machines du projet.

4.4 — Isoler le réseau
```bash
qvm-prefs -s insec-app netvm none
qvm-prefs -s insec-llm netvm none
qvm-prefs -s insec-vt netvm sys-net
```
- `qvm-prefs` : lit/modifie les préférences d'une VM.
- `-s` : set (définir).
- `insec-app` / nom de VM concernée.
- `netvm` : quelle VM fournit internet.
- `none` : AUCUN réseau. `sys-net` : via sys-net (internet).

Résultat : insec-app et l'LLM ne voient jamais internet ; seule insec-vt
en a — et uniquement pour VirusTotal.

4.5 — Diesel : configurer la RAM (recommandé pour LM Studio, onéreux)
```bash
qvm-prefs -s insec-llm memory 4096
qvm-prefs -s insec-llm vcpus 2
```
- `memory 4096` : 4 Go de RAM réservée.
- `vcpus 2` : 2 cœurs de processeur.
Ajustez selon votre machine (si 16 Go, `memory 8192` pour le LLM okay).

4.6 — Démarrer nos VMs pour la première fois
```bash
qvm-start insec-app; qvm-start insec-llm; qvm-start insec-vt
```

---

## Phase 5 — Installer l'application dans insec-app

Nous partons du principe que votre dépôt `InSecureDevice` est disponible
(sur une clé USB chiffrée, ou accessible sur un de vos supports de travail).
L'installation se fait **dans la VM**, pas dans dom0.

5.1 — Ouvrir un terminal dans insec-app
```bash
qvm-run insec-app xterm
```

5.2 — Dépendances système (noyau, Python, capstone pour le désassemblage)

dans insec-app :
```bash
sudo apt update
sudo apt install -y python3-venv python3-pip python3-dev build-essential
```
- `apt update` : actualise la liste des paquets disponibles.
- `install -y` : installe, `-y` = "oui" sans demander confirmation.

5.3 — Copier le code source (via un moyen air-gapped)
Si vous avez le dossier en clé USB :
```bash
# côté dom0 (si support physique) :
qvm-copy-to-vm insec-app /mnt/usb/InSecureDevice
```
Si vous travaillez depuis votre PC Windows :
```bash
# EPONYME : utilisez votre mécanisme habituel (rclone/copy via NetVM innocente)
# mais rappel : JAMAIS par internet. Utilisez sys-usb → insec-app.
```
Ensuite, à l'intérieur de insec-app, déplacez :
```bash
cd ~
mv InSecureDevice app-forensique
cd app-forensique
```

5.4 — Créer un environnement virtuel Python (isolé, "venv")
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install .                                  # installe l'app en mode édition
```
- `python3 -m venv .venv` : crée un environnement Python local, propre.
- `source .venv/bin/activate` : l'active (on "entre" dedans).
- `pip install .` : installe notre paquet à partir du dossier courant.

5.5 — Configurer l'environnement (les secrets / paramètres locaux)

Créé dans `~/.config/insecured/env.sh` :
```bash
export AI_BACKEND="openai"          # ou "dev" pour essayer sans IA
export AI_MODEL="qwen/qwen2.5-coder-14b"
export AI_BASE_URL="http://10.8.0.2:1234"    # IP RÉELLE de insec-llm !!
export VT_API_KEY="CLÉ_RÉELLE_VIRUSTOTAL"    # uniquement dans insec-vt
```
Puis chargez ce fichier au démarrage :
```bash
echo "source ~/.config/insecured/env.sh" >> ~/.bashrc
```

> 🔐 **Règle de fuite des secrets** : insec-app contient la clé LLM (adresse
> interne inoffensive) ; **seule insec-vt** a la clé VirusTotal. On ne met
> jamais la clé VT dans insec-app (même si l'app le permet — on va lui
> passer une valeur factice là).

5.6 — Lancer l'application
```bash
.venv/bin/python -m insecured
```
Une fenêtre s'ouvre : c'est l'app de analyse. En mode `AI_BACKEND=dev`
elle fonctionne sans IA pour le premier essai ; passez `openai` quand
votre LLM insec-llm est up.

---

## Phase 6 — Raccorder le LLM (insec-llm) + le média USB (qvm-block)

6.1 — LM Studio dans insec-llm
Installez LM Studio (ou Ollama) **dans insec-llm** (VM air-gapped) :
```bash
wget https://.../lmstudio-linux.tar.gz    # via une VM internet → insec-llm
```
hmm — rappel : c'est air-gapped. Le moyen propre : téléchargez le binaire
dans `insec-vt`, puis copiez vers `insec-llm` en LAN (insec-vt et insec-llm
peuvent se parler par le réseau LocalNet dédié, ou par qvm-copy).
Puis lancez  LM Studio en écoutant sur :
```bash
export GIN_MODE=release
lm-studio --server --host 0.0.0.0 --port 1234
```
- `0.0.0.0` : écoute sur toute l'interface réseau de insec-llm.
- insec-app y accède par `http://10.8.0.2:1234` (IP que vous avez pu obtenir
  avec `ip addr` dans insec-llm).

6.2 — Brancher le support d'enquête (USB) :
Depuis dom0 :
```bash
qvm-block attach insec-app sys-usb:sda
```
- `qvm-block` : outil de gestion des blocs (disques) USB.
- `attach insec-app` : on l'offre à insec-app.
- `sys-usb:sda` : le disque `sda` présent dans sys-usb (vérifiez le nom
  avec `qvm-block list` avant).

dans insec-app, le support apparaît comme `/dev/xvdi` (ou similaire) —
ainsi l'app le monte via son module `mount` (par défaut en lecture seule).

---

## Phase 7 — Run d'essai (dev, puis réel)

7.1 — Essai hors IA (dev)
```bash
cd ~/app-forensique
source .venv/bin/activate
export AI_BACKEND=dev
.venv/bin/python -m insecured
```
L'analyse doit tourner sans requête LLM, et produire un rapport.

7.2 — Essai avec LLM
- Assurez-vous que insec-llm répond (voir Phase 6.1).
- Remettez `export AI_BACKEND=openai` et `AI_MODEL=...`.
- Relancez et vérifiez dans le log l'étape `IA : <fichier>` → requête réellement
  envoyée, et l'export `RAPPORTS/rapport_<cas>_<date>.md`.

7.3 — Essai avec VirusTotal réel
- Dans `insec-vt` uniquement : configurer `VT_API_KEY` réelle.
- dans insec-app, l'étape VT doit afficher les réponses de l'API sans erreur.

---

## Dépannage rapide (Q&A)

**Q : `qvm-block` me renvoie « No such device » ?**
→ vérifiez le nom exact : `qvm-block list` ; souvent `sda` ou `sdb`.

**Q : l'app ne parle pas à l'LLM ?**
→ dans insec-app : `curl http://10.8.0.2:1234/v1/models` (devra répondre).
→ sinon la NetVM de insec-llm n'est pas `none` mais il n'est pas sur le même
  LAN : mettez les deux sur `none` et reliez via un `qvm-prefs` localhost.

**Q : quel modèle choisir ?**
→ `qwen2.5-coder-14b` est un bon compromis forensique (14B, compatible
  lm-chat). Si machine légère : `qwen2.5-coder-7b`.

**Q : l'analyse prend longtemps / l'app « reste bloqué » dans « IA rédige » ?**
→ c'est le garde-fou temporel (30 s) et l'export disque qui existent déjà
  dans le code : si plus de 30 s, l'app écrit un rapport **sans IA** dans
  `RAPPORTS/`. Pas de gel : c'est prévu.

---

## Synthèse (checklist aller-retour)
- [x] Phase 1 : vérifs ISO (SHA-256 + PGP)      — obligatoire
- [x] Phase 2 : install LUKS + passphrase
- [x] Phase 3 : mises à jour dom0 + templates
- [x] Phase 4 : `insec-app` netvm=none / `insec-llm` netvm=none / `insec-vt` netvm=sys-net
- [x] Phase 5 : insecured installé dans insec-app (venv) + env.sh
- [x] Phase 6 : LLM dans insec-llm + support USB attaché `qvm-block`
- [x] Phase 7 : run dev → run LLM → run VT
