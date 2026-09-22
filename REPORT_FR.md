# Rapport d'avancement — InSecureDevice

## 1. Contexte

Le projet vise un produit open-source destiné à la criminalistique numérique (forensique).
L'objectif est de **protéger le poste de travail forensique et son réseau** lorsqu'un
équipement non fiable (disque dur, clé USB, média de stockage) y est connecté pour analyse.

## 2. Le problème central

Lors d'une analyse forensique classique, on connecte le support saisi au poste de travail
pour créer une image forensique et analyser les données. Or, ce média est **potentiellement
hostile** :

- il peut contenir un **malware** qui s'exécute dès la connexion ;
- il peut forcer l'installation de **pilotes malveillants** ou de programmes au démarrage ;
- il peut **altérer ou détruire les preuves** présentes sur la machine ;
- il peut être contrôlé à distance par un attaquant pour mener une attaque via le câble.

Le problème n'est pas la protection du média (assurée par les **write-blockers**), mais la
protection de **la machine d'analyse elle-même**.

## 3. Évolution de la portée

La portée a été définie comme suit : **analyse statique de médias USB et de disques de
stockage** connectés au poste de travail.

Sont exclus : l'extraction mobile, Cellebrite et les outils propriétaires (MSAB XRY, etc.),
ainsi que l'extraction « live ».

## 4. Direction de solution retenue

La solution repose sur **Qubes OS**, un système d'exploitation à isolation forte basé sur
l'hyperviseur **Xen**, organisé en machines virtuelles (qubes) isolées les unes des autres.

Comparaison réalisée : un **VM complet** (Qubes/Xen) est nettement plus sûr qu'un conteneur
(Docker), car le conteneur partage le noyau de l'hôte. Les attaques au niveau noyau d'un
média hostile pourraient donc s'échapper. Le VM garantit une isolation matérielle complète.

## 5. Architecture proposée

```
Poste forensique Qubes OS
│
├── dom0 (noyau hôte, aucun média connecté) ── session journalisée pour la traçabilité
│
├── sys-usb          → contrôle les ports USB / contrôleurs, c'est là que le média est branché
│
└── Qube d'analyse jetable (Disposable VM), SANS réseau (air-gapped)
     ├── le média y est monté via passage de bloc (qvm-block)
     ├── les outils d'analyse statique y tournent (dd, imagier, bulk_extractor, Autopsy…)
     └── le qube est détruit après chaque cas → nouvelle session propre
```

Principes clés :
- le **média n'est jamais monté sur l'hôte** (dom0), seulement dans le qube d'analyse ;
- le qube d'analyse est **air-gapped** le temps de la connexion ;
- les opérations d'attachement/détachement sont **journalisées** (preuve de manipulation) ;
- **un cas = un qube jetable** : toute infection est écartée avec la destruction du qube.

## 6. Position par rapport aux outils existants

- Le projet **n'est pas** un remplaçant de Cellebrite ou d'autres outils.
- Il **s'articule avec les write-blockers** : ceux-ci protègent le support saisi (intégrité de
  la preuve), tandis qu'InSecureDevice protège la machine d'analyse et le réseau.

## 7. Décisions prises

- [x] Problème central défini : protéger poste + réseau face à un média hostile.
- [x] Portée : analyse statique de médias USB/disques.
- [x] Direction : Qubes OS (VM Xen), pas de conteneurs.
- [x] Placement : sys-usb + qube d'analyse jetable air-gapped.
- [x] Bénéficiaires : forces de l'ordre.

## 8. Questions ouvertes

- [ ] Choix de la pile d'outils d'analyse statique dans le qube jetable.
- [ ] Workflow d'export et de préservation des preuves (image forensique, hash) après
      destruction du qube.
- [ ] Automatisation du flux par cas : créer le qube → attacher le média → analyser → détruire.
- [ ] Modèle de livraison : image « usine » du poste forensique, ou couche d'automatisation
      à déployer sur Qubes existant.

## 9. Conclusion

Le projet a atteint le stade de la **définition** : le problème est clair, la portée est
maîtrisée et l'architecture d'isolation (Qubes OS) est choisie. Il reste à concevoir le
**flux opératoire détaillé** et à définir les **outils et la préservation des preuves** avant
de passer à la partie développement.

**Niveau actuel : phase de conception / cadrage.**