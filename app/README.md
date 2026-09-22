# InSecureDevice — Application

Application desktop d'analyse forensique statique isolée (Qubes OS).
Stack : **Python + PySide6**, pipeline modulaire, intégration Qubes derrière une interface.

## Structure

```
app/
├── pyproject.toml / requirements.txt
├── src/insecured/
│   ├── __main__.py           # point d'entrée GUI
│   ├── config.py             # choix backend (env)
│   ├── models/               # Case, EvidenceFile, PipelineResult
│   ├── pipeline/
│   │   ├── base.py           # Stage (abstrait) + StageContext
│   │   ├── orchestrator.py   # exécution séquentielle des stages
│   │   └── stages/
│   │       ├── inventory.py  # 1. inventaire des fichiers
│   │       ├── hashing.py    # 2. SHA-256 par fichier
│   │       ├── metadata.py   # 3. métadonnées + magic numbers
│   │       ├── anomalies.py  # 4. détection d'anomalies
│   │       └── ai_analysis.py# 5. analyse IA on-premise
│   ├── qubes/                # bridge Qubes (qvm-block/qrexec) + fallback dev
│   └── ui/                   # PySide6 : MainWindow, EvidenceTable, panel de cas
├── tests/                    # tests de la pipeline (pytest)
└── demo_run.py               # démo CLI sans GUI
```

## Modes d'exécution

| Variable | Valeur | Effet |
|---|---|---|
| `QUBES_BACKEND` | `dev` (défaut) | Le "média" = dossier `DEV_MEDIA` ; aucun Qubes requis |
| `QUBES_BACKEND` | `qvm` | Vrai poste Qubes (`qvm-block` sys-usb/dom0) |
| `AI_BACKEND` | `dev` | Sortie IA simulée (hors poste) |
| `AI_BACKEND` | `ollama` | Modèle local via Ollama (on-premise, air-gapped) |
| `AI_BACKEND` | `cli` | Binaire CLI local |
| `AI_MODEL` | `llama3` | Nom du modèle Ollama |

## Démarrage

```bash
pip install -e .[dev]          # ou: pip install -r requirements.txt
python -m insecured            # GUI
python demo_run.py             # démo CLI
python -m pytest tests -q      # tests
```

## Prochaines itérations

- [ ] Signal udev+dans sys-usb → qrexec vers qube app
- [ ] Appel des outils Qubes (imagerie dcfldd, montage RO)
- [ ] Backend Ollama validé sur poste air-gapped
- [ ] Export d'un rapport de cas (JSON/Markdown) vers le qube évidence