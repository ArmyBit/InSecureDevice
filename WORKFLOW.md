# InSecureDevice — Workflow d'analyse forensique sur Qubes OS

> Diagrammes Mermaid. Pour les visualiser : ouvrir dans VSCode (extension Mermaid),
> Typora, GitHub, ou tout outil compatible Mermaid.

## 1. Vue d'ensemble du workflow

```mermaid
flowchart TD
    A[["Début de cas — média saisi"]] --> B["Brancher le média<br/>sur un port contrôlé par sys-usb"]
    B --> C{"Type de média ?"}
    C -->|"Clé USB / carte"| D["Attachement bloc — qvm-block<br/>(depuis sys-usb)"]
    C -->|"Disque / SSD externe"| D
    D --> E["Créer un qube d'imagerie jetable<br/>(DispVM)"]
    E --> F["Attacher la source (média via sys-usb)<br/>+ cible (volume qube évidence)"]
    F --> G["Journal dom0 : attachement enregistré"]
    G --> H["Accès lecture seule logicielle<br/>(RO mount / O_RDONLY)"]
    H --> I["Imagerie : dcfldd → image .dd<br/>+ hash SHA-256 en continu"]
    I --> J["Écriture directe de l'image<br/>dans le qube évidence"]
    J --> K{"Hash vérifié ?"}
    K -->|"Non conforme"| L["Analyser / refaire capture"]
    K -->|"Conforme"| M["Média débranché — l'image<br/>reste la source de la preuve"]
    M --> N["Créer le qube d'analyse jetable<br/>(DispVM par cas)"]
    N --> O["Monter l'image depuis le qube évidence<br/>(lecture seule)"]
    O --> P["Pipeline d'analyse (app desktop)"]
    P --> Q["Exporter rapports/artefacts<br/>vers le qube évidence (qrexec)"]
    Q --> R{"Hash post-export vérifié ?"}
    R -->|"OK"| S["Détruire le qube d'analyse jetable"]
    S --> T["Journal final de session (traçabilité)"]
    T --> U[["Fin de cas"]]
    R -->|"Échec"| Q
    L --> H
```

## 2. Isolation & flux système

```mermaid
flowchart LR
    subgraph Host[Poste forensique — Qubes OS]
        dom0["dom0<br/>(journalisation, aucun média monté)"]
        sysusb["sys-usb<br/>(contrôle des ports USB)"]
        imaq["Qube d'imagerie jetable<br/>(DispVM, air-gapped)"]
        appq["Qube applicatif dédié<br/>(app desktop Python/PySide)"]
        anaq["Qube d'analyse jetable<br/>(DispVM par cas)"]
        evid["Qube évidence<br/>(image .dd + hash + rapports)"]
    end

    Device["Média saisi<br/>(clé USB / disque)"]

    Device -->|"branchement physique"| sysusb
    sysusb -->|"qvm-block (source)"| imaq
    evid -->|"qvm-block (cible: volume évidence)"| imaq
    imaq -->|"dcfldd → image .dd + SHA-256"| evid
    appq -->|"signal udev + qrexec"| sysusb
    evid -->|"qvm-block (image, RO)"| anaq
    anaq -->|"pipeline d'analyse (app desktop)"| appq
    anaq -->|"export rapports (qrexec)"| evid
    dom0 -.->|"journal session"| sysusb
    dom0 -.->|"journal session"| imaq
    dom0 -.->|"journal session"| anaq
```

## 3. Cycle de vie d'un cas (un cas = des qubes jetables)

```mermaid
stateDiagram-v2
    [*] --> Brancher_média : média saisi
    Brancher_média --> Imagerie : DispVM imagier + qvm-block
    Imagerie --> Vérification_hash : dcfldd + SHA-256
    Vérification_hash --> Image_évidence : image .dd archivée
    Image_évidence --> Analyse : DispVM analyse + image montée RO
    Analyse --> Pipeline : app desktop (inventaire → hash → meta → anomalies → IA)
    Pipeline --> Export_rapports : qrexec vers qube évidence
    Export_rapports --> Vérification_post : hash post-export
    Vérification_post --> Détruire_qube : cas clôturé
    Détruire_qube --> Journal_final : traçabilité dom0
    Journal_final --> [*]
    Détruire_qube --> [*] : toute infection écartée
```

## 4. Séquence d'acquisition (imagerie forensique)

```mermaid
sequenceDiagram
    participant Op as Opérateur
    participant Su as sys-usb
    participant D as dom0
    participant I as Qube imagerie (DispVM)
    participant E as Qube évidence

    Op->>Su: Brancher le média sur le port dédié
    Su->>D: Événement de connexion USB
    D->>D: Journal: média détecté (date/heure/série)
    Op->>AppApp: Lancer l'acquisition (app desktop)
    AppApp->>D: qvm-block attach (source média)
    D->>Su: Demande d'attachement bloc source
    Su->>I: Attachement bloc source (RO)
    AppApp->>D: qvm-block attach (volume évidence)
    D->>E: Demande d'attachement bloc cible
    E->>I: Attachement bloc cible (volume évidence)
    I->>I: dcfldd → image .dd + SHA-256 (écriture directe)
    I->>E: Écriture de l'image dans le volume évidence
    I->>I: Vérification du hash (recalcul)
    I->>E: Rapport d'acquisition (opérateur/date/hash)
    Op->>D: Débrancher / détacher le média
    D->>D: Journal: détachement enregistré
    Op->>I: Détruire le qube d'imagerie jetable
```

## 5. Pipeline applicative (app desktop — qube applicatif dédié)

```mermaid
flowchart LR
    Sig["Signal udev+qrexec<br/>(média connecté)"] --> A["Inventaire<br/>(liste des fichiers)"]
    A --> B["Hachage<br/>(extraction hash fichiers)"]
    B --> C["Métadonnées + magic numbers<br/>(lecture des fichiers)"]
    C --> D["Détection d'anomalies<br/>(corrélation hash/meta/magic)"]
    D --> E["Analyse & reverse engineering<br/>assistés par IA"]
    E --> R["Rapport de cas<br/>(export vers qube évidence)"]
```

## 6. Décisions / règles de sécurité

```mermaid
flowchart LR
    Begin["Média connecté"] --> Q1{"Type stockage (masse) ?"}
    Q1 -->|"Oui"| R1["Attachement bloc (qvm-block) — recommandé"]
    Q1 -->|"Non / périphérique USB"| R2["Attachement USB (qubes-usb-proxy)<br/>→ risque plus élevé, à éviter"]
    R1 --> Q2{"Image créée + hash OK ?"}
    R2 --> Q2
    Q2 -->|"Oui"| R3["Image archivée dans le qube évidence"]
    Q2 -->|"Non"| R4["Refaire l'acquisition (monter RO)"]
    R3 --> Q3{"L'analyse est-elle faite sur l'image ?"}
    Q3 -->|"Oui"| R5["Le média peut être débranché"]
    Q3 -->|"Non"| R6["L'analyse doit rester sur l'image"]
    R5 --> R7["Exporter rapports → évidence, puis détruire les qubes jetables"]
```