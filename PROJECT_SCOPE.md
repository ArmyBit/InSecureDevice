# Project Scope: InSecureDevice

## Overview

InSecureDevice is an open-source, Qubes OS-based solution that safely connects **USB and
storage disks** to a forensic workstation for **static analysis**, protecting the workstation
and its network from the untrusted device.

## Target Focus

- **Analysis type:** static analysis of USB storage and external disks (no live mobile
  extraction; no Cellebrite or proprietary extraction tools)
- **Primary users:** Law enforcement (police, agencies, first responders)
- **Product form:** open-source, built on Qubes OS isolation

## Core Problem We Solve

When a suspect device is connected to a forensics workstation (to build a forensic image via
existing tools), the **workstation itself is not safe from the device**. Connecting a device
risks infecting or destroying the entire OS and all evidence on the workstation.

### Threat Model (priority risks)

- **Malware auto-execution** - malware stored on the device runs upon connection
- **Malicious drivers / autostart** - the device forces malicious driver installs / autostart
- **Evidence tampering & destruction** - malware spreads from device to workstation and destroys the evidence
- **Remote / networked attacks** - an attacker controls the device remotely and attacks through it

### Devices In Scope

- USB storage (thumb drives, memory cards, external drives)
- Storage disks / SSDs connected to the host for analysis

### Out of Scope

- Mobile extraction (iOS / Android physical & logical)
- Cellebrite / MSAB XRY / other proprietary extraction tools
- Live extraction workflows

### Solution Direction

**Qubes OS based.** The product works independently of existing extraction tools and is not a
replacement for them.

#### Application architecture

```
Media USB / disque de stockage
        │  branchement physique
        ▼
   ┌─────────────┐
   │   sys-usb   │  contrôle des ports USB / contrôleurs de stockage
   └─────┬───────┘
         │  Attachement bloc : qvm-block (depuis sys-usb)
         ▼
   ┌────────────────────────────────────┐
   │  VM dédié d'analyse (DispVM par cas) │  monte les fichiers suspects
   │  - montage en lecture seule         │  + journalise l'accès
   │  - analyse statique isolée          │  - air-gapped (pas de NetVM)
   │  - export preuves via qrexec        │
   └────────────────────────────────────┘
         │  export contrôlé (qrexec)
         ▼
   ┌─────────────┐
   │  Qube évidence │  conservation des preuves / images forensiques
   └─────────────┘
```

Décisions structurantes :
- **VM dédié = Disposable VM, un par cas** - créé à l'ouverture du cas, détruit à la clôture ;
  toute infection du média est écartée avec la destruction du qube.
- **Rôle du VM dédié : montage + journalisation** - il contrôle l'accès au média et journalise,
  l'analyse statique reste isolée dans une sous-zone.
- **Rattachement du média : attachement bloc via `qvm-block`** (recommandé par Qubes) plutôt que
  passthrough USB complet, pour réduire la surface d'attaque.

**Support de travail de l'analyse : image forensique, pas le média branché.**
1. Imagerie du média (dd / imagier) + hash SHA-256 de référence
2. **L'image est archivée dans le qube évidence** (stockage persistant)
3. La pipeline travaille sur l'image forensique (le périphérique peut être débranché)
4. Le VM jetable monte l'image depuis le qube évidence et rend ses résultats avant destruction

Ceci garantit chaîne de traçabilité (image + hash figés) et indépendance vis-à-vis du
périphérique physique pendant toute l'analyse.

#### Création de l'image forensique

- **Format : raw (.dd) + hash SHA-256 séparé** - simple, universel, lisible par tout outil
- **Protection d'écriture : logicielle (lecture seule)** - montage RO + lecture `O_RDONLY`,
  pas de write-blocker matériel dans la chaîne
- **Écriture : directe dans le qube évidence** - le qube évidence expose un volume (bloc),
  le qube d'imagerie (DispVM) y écrit l'image pendant l'acquisition
- Chaîne d'acquisition : média → sys-usb → `qvm-block` (source) + volume évidence (cible)
  → `dcfldd` (hash in-band SHA-256) → vérification hash → rapport d'acquisition

#### Application (Qube applicatif dédié)

L'application est une **application de bureau (desktop)** tournant dans son **propre qube
dédié** dans Qubes, entre sys-usb et le VM d'analyse.
**Signal de connexion : udev/hotplug dans sys-usb, propagé par qrexec à l'application.**

**Stack :** Python + PySide/Qt - **GUI riche** (l'outil de travail quotidien de l'opérateur).
**Structure interne :** pipeline modulaire (stages orchestres par un orchestrateur).

Pipeline applicative (déclenchée dès qu'un support est connecté) :
1. **Signal** - un support est branché ; udev le détecte, qrexec alerte l'application
2. **Inventaire** - l'application liste les fichiers présents sur le média
3. **Hachage** - extraction des empreintes (hash) de chaque fichier
4. **Métadonnées + magic numbers** - lecture des métadonnées et des nombres magiques des fichiers
5. **Détection d'anomalies** - corrélation des hash / métadonnées / magic numbers
6. **Analyse & reverse engineering assistés par IA** - modèle **on-premise (local, air-gapped)**

#### How it works

- **sys-usb qube** controls all USB/storage connections - the host (dom0 / analysis qubes)
  never touches the device controller directly
- The device is mounted inside a **disposable analysis VM per case**, never on the host
- The dedicated VM **mounts + logs access**; static analysis runs isolated
- **Air-gapped** (no NetVM) while the device is connected
- Session attach/detach is **logged in dom0** for audit/tamper evidence
- A new case starts clean via a fresh disposable qube

#### Relationship to write-blockers

Write-blockers protect the **seized device** (prevent modification of evidence data).
This product is complementary: it protects the **forensic workstation and the network** from
the untrusted device.

#### Native Qubes mechanisms leveraged

- `qvm-block` block-device attach (preferred over raw USB passthrough for storage)
- `qubes-usb-proxy` / sys-usb for USB device passthrough
- Disposable VMs for clean per-case sessions
- No-NetVM policy for air-gapping
- qrexec for controlled inter-VM file transfer (evidence export)

## Goals

- [x] Define the core issue current tools fail to solve
- [x] Define analysis scope (static analysis of USB/storage disks)
- [x] Define solution direction (Qubes OS isolation)
- [x] Decide workflow placement (sys-usb + disposable analysis qube)
- [x] Decide application architecture (DispVM par cas, montage + journalisation, qvm-block)
- [x] Define application pipeline (signal -> inventaire -> hash -> meta/magic -> anomalies -> IA)
- [x] Decide AI model hosting (on-premise, local, air-gapped)
- [x] Decide app form (desktop, Python + PySide/Qt, GUI riche, pipeline modulaire)
- [x] Decide analysis working copy (image forensique archivée dans le qube évidence)
- [x] Define imaging format (Raw + SHA-256, protection logicielle RO, écriture directe évidence)
- [ ] Define OS/tool stack for the analysis qube
- [ ] Define evidence export & preservation workflow
- [ ] Define per-case automation (spawn qube -> attach -> analyze -> destroy)

## Non-Goals

- Not a mobile extraction tool (no iOS/Android extraction)
- No integration or replacement for Cellebrite / proprietary tools
- Does not run on non-Qubes hosts