/**
 * Seed data for the demo build. No backend, no network: everything the demo shows is here.
 *
 * Bodies are real prose rather than lorem ipsum, because the demo exists to judge reading
 * comfort and the text-to-speech, and both fall apart on filler text.
 */

export interface SeedFolder {
	id: string;
	name: string;
}

export interface SeedFeed {
	id: string;
	folder_id: string;
	title: string;
	url: string;
}

export interface SeedArticle {
	id: string;
	feed_id: string;
	author_name: string;
	category_name: string;
	title: string;
	summary: string;
	paragraphs: string[];
	keywords: string[];
	published_at: string;
	image_hue: number;
}

export const SEED_FOLDERS: SeedFolder[] = [
	{ id: 'folder-tech', name: 'Tech' },
	{ id: 'folder-design', name: 'Design' },
	{ id: 'folder-monde', name: 'Monde' },
	{ id: 'folder-science', name: 'Science' }
];

export const SEED_FEEDS: SeedFeed[] = [
	{
		id: 'feed-fibre',
		folder_id: 'folder-tech',
		title: 'Fibre Optique',
		url: 'https://fibre-optique.fr/feed.xml'
	},
	{
		id: 'feed-canal',
		folder_id: 'folder-tech',
		title: 'Canal Ouvert',
		url: 'https://canalouvert.net/rss'
	},
	{
		id: 'feed-sillage',
		folder_id: 'folder-monde',
		title: 'Sillage',
		url: 'https://sillage.media/atom.xml'
	},
	{
		id: 'feed-atelier',
		folder_id: 'folder-design',
		title: 'Atelier Papier',
		url: 'https://atelierpapier.studio/feed.json'
	},
	{
		id: 'feed-grille',
		folder_id: 'folder-design',
		title: 'Grille',
		url: 'https://grille.design/rss'
	},
	{
		id: 'feed-preprint',
		folder_id: 'folder-science',
		title: 'Preprint Digest',
		url: 'https://preprint.digest/feed'
	}
];

const CLOSING = [
	"Reste la question de l'échelle. Sur un corpus de plusieurs milliers d'articles, un tri par pertinence apprise ne remplace pas une curation humaine : il la rend soutenable, en écartant d'abord le bruit avant d'exposer les signaux faibles.",
	"Rien de tout cela ne demande une infrastructure considérable. Un serveur domestique, quelques centaines de mégaoctets et un peu de patience suffisent à reproduire l'essentiel, ce qui explique la vitalité persistante de cet écosystème."
];

export const SEED_ARTICLES: SeedArticle[] = [
	{
		id: 'article-1',
		feed_id: 'feed-fibre',
		author_name: 'Claire Baudet',
		category_name: 'Lecture',
		title: 'Le retour du web lent, ou comment relire à son rythme',
		summary:
			"Un mouvement de fond remet la lecture longue au centre : moins de flux, plus d'attention.",
		keywords: ['lecture', 'attention', 'web lent'],
		published_at: '2026-08-13T07:20:00Z',
		image_hue: 265,
		paragraphs: [
			"On a longtemps mesuré la veille au volume : nombre de sources suivies, nombre d'articles parcourus, nombre de notifications traitées dans la journée. Cette métrique avait le mérite d'être simple, et le défaut d'être fausse. Elle décrit une activité, pas une compréhension.",
			"Les lecteurs qui reviennent aujourd'hui vers des outils plus lents ne cherchent pas la nostalgie d'un web disparu. Ils cherchent une contrainte : décider en amont de ce qu'ils vont lire, plutôt que de laisser un fil de recommandation décider à leur place, article après article, sans jamais annoncer la fin.",
			"La différence tient à un détail d'interface. Une file qui se termine change le rapport au temps : on sait où on en est, on sait quand on a fini. Un flux infini ne le permet pas, et cette impossibilité n'est pas un accident technique mais un choix de conception, assumé par les plateformes dont le revenu dépend du temps passé.",
			"Les études sur l'attention convergent sur un point rarement discuté : ce n'est pas l'interruption elle-même qui coûte le plus cher, c'est le coût de reprise. Retrouver le fil d'un raisonnement après une coupure demande davantage d'effort que de le suivre d'un bout à l'autre, et cet effort est invisible dans toutes les mesures d'usage.",
			"D'où l'intérêt, pour un lecteur, d'outils qui mémorisent la position exacte dans un texte plutôt que le simple fait de l'avoir ouvert. Reprendre au paragraphe près, sur un autre appareil, supprime précisément ce coût de reprise.",
			"Les partisans du web lent se méfient d'ailleurs de leur propre vocabulaire. Personne ne défend la lenteur pour elle-même : une dépêche de trois lignes n'a aucun besoin d'être ralentie. Ce qui est défendu, c'est le droit de traiter différemment deux textes qui n'ont pas la même densité, là où un fil unique les aligne sans distinction.",
			"Cette distinction demande un signal, et le temps de lecture estimé en est un, imparfait mais honnête. Il ne dit rien de la difficulté d'un texte, mais il permet d'ajuster ce qu'on ouvre à ce dont on dispose : sept minutes avant une réunion, ce n'est pas le moment d'entamer une enquête au long cours.",
			"Le même raisonnement vaut pour l'écoute. Une file audio dont la durée totale est affichée se remplit autrement qu'une liste comptée en nombre d'éléments, parce que la contrainte de temps devient visible au moment de choisir plutôt qu'au milieu du trajet.",
			CLOSING[0]
		]
	},
	{
		id: 'article-2',
		feed_id: 'feed-canal',
		author_name: 'Nadia Perrin',
		category_name: 'Outils',
		title: "Les lecteurs RSS n'ont jamais disparu",
		summary:
			"Douze ans après Google Reader, l'écosystème auto-hébergé n'a jamais été aussi vivant.",
		keywords: ['rss', 'auto-hébergement', 'veille'],
		published_at: '2026-08-13T06:05:00Z',
		image_hue: 200,
		paragraphs: [
			"La fermeture de Google Reader en 2013 a été racontée comme la fin d'une époque. Elle a surtout été la fin d'un monopole. Les années qui ont suivi ont vu apparaître plus d'implémentations de lecteurs de flux que la décennie précédente, la plupart libres, beaucoup auto-hébergeables.",
			"Le format lui-même n'a pas bougé. Un fichier XML, une liste d'entrées, des dates de publication : la simplicité du protocole explique sa longévité. Aucune plateforme n'a jamais eu à autoriser quiconque à le lire, et c'est cette absence de permission à demander qui fait toute la différence.",
			"Ce qui a changé, c'est la couche au-dessus. Extraire un article lisible depuis une page saturée de bandeaux, détecter la langue, résumer, classer par intérêt : ces traitements demandaient hier une infrastructure, ils tiennent aujourd'hui sur une machine domestique.",
			"Le point de bascule s'est joué sur l'extraction de contenu. Les bibliothèques modernes retirent le décor d'un site avec une fiabilité qui rendait, il y a dix ans encore, l'exercice décevant : on récupérait le menu, les articles connexes, parfois le pied de page, rarement le texte seul.",
			"L'autre progrès est passé inaperçu parce qu'il est ennuyeux : la gestion des erreurs. Un flux qui répond en cinq cents, un certificat expiré, un site qui change d'adresse sans redirection — ces incidents banals faisaient dérailler les premiers agrégateurs et sont aujourd'hui traités comme des états normaux, avec reprise et journalisation.",
			"Il faut y ajouter la question du stockage. Conserver plusieurs années d'articles nettoyés représente quelques gigaoctets, ce qui était considérable sur un serveur partagé et ne l'est plus du tout sur un disque domestique. La conservation intégrale, longtemps réservée aux plateformes, est devenue une option par défaut.",
			"Reste un point que la technique ne réglera pas : le nombre de sites qui publient encore un flux complet plutôt qu'un extrait tronqué. C'est une décision éditoriale, et elle varie beaucoup d'un secteur à l'autre.",
			CLOSING[1]
		]
	},
	{
		id: 'article-3',
		feed_id: 'feed-sillage',
		author_name: 'Yann Delcourt',
		category_name: 'Algorithmes',
		title: 'Apprendre les goûts sans profiler',
		summary:
			"Des modèles locaux suffisent à classer un flux personnel, sans envoyer une ligne au cloud.",
		keywords: ['recommandation', 'vie privée', 'tf-idf'],
		published_at: '2026-08-12T18:40:00Z',
		image_hue: 150,
		paragraphs: [
			"Une recommandation utile n'exige pas de connaître son lecteur. Elle exige de connaître ses signaux : ce qu'il ouvre, ce qu'il termine, ce qu'il écarte au bout de trois lignes. Ces signaux sont produits localement et peuvent y rester.",
			"La démonstration est presque banale sur le plan technique. Une pondération de termes par fréquence inverse, une racinisation adaptée à la langue, quelques compteurs par auteur et par source : on obtient un classement qui bat largement l'ordre chronologique, sans réseau de neurones et sans serveur.",
			"L'intérêt n'est pas la performance brute mais la réversibilité. Un score appris localement peut être remis à zéro, inspecté, corrigé. Un profil publicitaire construit ailleurs ne peut être ni consulté ni annulé, et survit généralement à la fermeture du compte qui l'a produit.",
			"Il y a une limite honnête à poser : ce type de modèle ne découvre rien. Il renforce ce qu'il observe, et resserre progressivement le champ. C'est pourquoi un bon lecteur garde un mode qui présente délibérément des articles que le score n'aurait pas remontés.",
			"La question du signal négatif mérite un traitement à part. Écarter un article peut vouloir dire « pas ce sujet », « pas cette source » ou simplement « pas maintenant », et confondre les trois produit un modèle qui apprend de travers. Séparer les axes — avis, mise de côté, favori, lecture terminée — coûte quelques colonnes en base et évite cette confusion.",
			"L'évaluation reste le point faible de l'exercice. Sans jeu de test, on ne mesure rien, et un lecteur unique ne produira jamais assez d'annotations pour valider quoi que ce soit statistiquement. La seule évaluation honnête est subjective : est-ce que les cinq premiers articles de la journée méritent d'être lus ?",
			"C'est peu satisfaisant sur le plan méthodologique, et parfaitement suffisant sur le plan pratique. Un classement personnel n'a pas à être juste dans l'absolu, il a à être meilleur que l'ordre d'arrivée.",
			CLOSING[0]
		]
	},
	{
		id: 'article-4',
		feed_id: 'feed-atelier',
		author_name: 'Inès Roussel',
		category_name: 'Interaction',
		title: "Le geste comme signal d'intention",
		summary: "Le swipe n'est pas qu'une commodité tactile : c'est une donnée de préférence.",
		keywords: ['geste', 'interface', 'préférence'],
		published_at: '2026-08-12T15:10:00Z',
		image_hue: 25,
		paragraphs: [
			"Balayer une carte vers la droite ou vers la gauche paraît anodin. C'est pourtant l'une des rares interactions où le coût de l'erreur est presque nul et où l'intention est parfaitement lisible : personne ne balaie par distraction.",
			"Les concepteurs d'applications de rencontre ont popularisé le geste, mais ils en ont aussi figé une version pauvre, à deux directions. Rien n'oblige à s'y tenir : la quatrième direction, vers le haut ou vers le bas, ouvre un axe supplémentaire sans ajouter le moindre bouton.",
			"Le point délicat est ailleurs. Un geste doit rester annulable, sinon il devient anxiogène : on hésite, on ralentit, et l'avantage disparaît. Une annulation offerte pendant quelques secondes après l'action suffit à rétablir la confiance.",
			"Reste l'accessibilité, trop souvent traitée après coup. Un geste sans équivalent clavier est une fonctionnalité réservée à une partie des utilisateurs, et cette exclusion se répare mal une fois l'interface construite autour du pointeur.",
			"Le retour visuel pendant le geste fait le reste du travail. Une carte qui s'incline, un libellé qui apparaît sous le doigt, une couleur qui se renforce à mesure qu'on approche du seuil : le lecteur sait ce qui va se produire avant de relâcher, et le taux d'erreur s'effondre.",
			"Ce seuil mérite d'être choisi avec soin. Trop bas, l'interface vote à la place de l'utilisateur au moindre frôlement pendant un défilement. Trop haut, le geste devient un effort et perd l'avantage qui le rendait intéressant.",
			CLOSING[1]
		]
	},
	{
		id: 'article-5',
		feed_id: 'feed-atelier',
		author_name: 'Inès Roussel',
		category_name: 'Typographie',
		title: "Typographie d'écran : la revanche des serifs",
		summary:
			'Les écrans haute densité redonnent aux serifs de labeur leur place dans le corps de texte.',
		keywords: ['typographie', 'lisibilité', 'serif'],
		published_at: '2026-08-12T11:00:00Z',
		image_hue: 45,
		paragraphs: [
			"Le sans-serif a régné sur le web pour une raison technique : sur un écran à quatre-vingt-seize points par pouce, les empattements se transformaient en bouillie de pixels. Cette raison a disparu, mais l'habitude est restée.",
			"Les densités actuelles restituent des dessins de caractères pensés pour l'impression, y compris leurs détails fins. Un serif de labeur, choisi pour de longues plages de texte, retrouve à l'écran l'avantage qu'il avait sur le papier : un guidage horizontal de l'œil plus marqué.",
			"Le vrai levier de lisibilité reste ailleurs. La longueur de ligne, l'interlignage et le contraste pèsent davantage que le choix de la famille. Soixante-cinq à soixante-quinze signes par ligne, un interlignage autour de 1,6 : ces valeurs banales font plus pour le confort qu'aucun choix de fonte.",
			"Une interface de lecture gagne donc à distinguer deux registres : un serif pour le corps du texte et les titres, un sans-serif pour la navigation et les libellés d'action. Cette distinction n'est pas décorative, elle indique en permanence ce qui se lit et ce qui se clique.",
			"Le mode sombre complique l'affaire. Un caractère clair sur fond sombre paraît plus gras qu'il ne l'est, phénomène connu sous le nom d'irradiation. Les familles qui proposent une graisse intermédiaire permettent de compenser sans changer de fonte, ce que peu d'interfaces prennent la peine de faire.",
			"La taille de texte réglable pose une dernière contrainte, souvent mal traitée. Agrandir uniformément tous les niveaux préserve la hiérarchie ; agrandir le seul corps de texte finit par le rendre plus gros que ses propres sous-titres, et l'échelle typographique s'effondre.",
			"C'est pourquoi un réglage de confort gagne à agir sur la taille de base et à laisser les rapports faire le reste, plutôt que d'exposer une taille par niveau que personne n'a envie de régler.",
			CLOSING[0]
		]
	},
	{
		id: 'article-6',
		feed_id: 'feed-grille',
		author_name: 'Marc Estève',
		category_name: 'Composition',
		title: "Le nombre d'or est-il une superstition utile ?",
		summary:
			'Enquête sur φ dans les grilles contemporaines, entre outil de composition et mythe tenace.',
		keywords: ['grille', 'proportion', 'composition'],
		published_at: '2026-08-11T16:30:00Z',
		image_hue: 85,
		paragraphs: [
			"Peu de notions traversent autant de disciplines avec aussi peu de preuves. Le nombre d'or est invoqué en architecture, en peinture, en design d'interface, et l'examen des sources historiques réserve à chaque fois la même surprise : la proportion est plaquée après coup.",
			"Cela ne rend pas l'outil inutile. Une suite de rapports cohérents produit une hiérarchie visible, et peu importe que le rapport choisi vaille 1,618 ou 1,5 : c'est la cohérence entre les niveaux qui se perçoit, pas la valeur elle-même.",
			"L'échelle typographique moderne repose exactement sur ce principe. On fixe une taille de base et un rapport, on en déduit tous les niveaux. Changer la base met l'ensemble à l'échelle sans jamais casser les proportions, ce qui est précisément ce qu'on attend d'un réglage de taille de texte.",
			"Les grilles de mise en page suivent la même logique, avec une contrainte supplémentaire : elles doivent survivre au redimensionnement. Une proportion élégante sur un écran large devient illisible sur un téléphone, et aucune valeur magique ne protège de ce passage à l'échelle.",
			"D'où la préférence contemporaine pour des grilles qui se réorganisent par paliers plutôt que de se comprimer continûment. Le nombre de colonnes change, les proportions internes restent, et la composition tient sur toute la gamme d'écrans.",
			CLOSING[1]
		]
	},
	{
		id: 'article-7',
		feed_id: 'feed-fibre',
		author_name: 'Claire Baudet',
		category_name: 'Audio',
		title: 'La synthèse vocale du navigateur devient écoutable',
		summary:
			"La Web Speech API franchit le seuil du confort d'écoute prolongée, sans serveur.",
		keywords: ['synthèse vocale', 'audio', 'navigateur'],
		published_at: '2026-08-11T09:45:00Z',
		image_hue: 300,
		paragraphs: [
			"Pendant dix ans, la synthèse vocale intégrée aux navigateurs a servi surtout de démonstration technique. La prosodie était plate, les liaisons approximatives, et l'écoute devenait pénible bien avant la fin d'un article.",
			"Les voix embarquées dans les systèmes récents ont changé la donne. Elles restent en deçà d'un enregistrement humain, mais elles franchissent le seuil qui compte : on peut écouter vingt minutes sans fatigue particulière, ce qui suffit pour un article de fond.",
			"Un détail d'implémentation décide de la qualité perçue. Passer un texte entier à la synthèse produit régulièrement des arrêts au bout de quelques dizaines de secondes, selon le moteur. Découper par phrases et enchaîner soi-même les segments supprime le problème et permet, au passage, de suivre la progression.",
			"La pause réserve une autre surprise : elle est mal supportée par plusieurs implémentations, au point qu'il est souvent plus fiable d'interrompre puis de reprendre le segment courant depuis son début que de faire confiance à la mise en pause native.",
			"L'avantage décisif reste la confidentialité. Rien ne quitte l'appareil, aucun texte n'est envoyé à un service tiers pour être vocalisé, et l'écoute fonctionne hors ligne une fois l'article chargé.",
			"La vitesse de lecture mérite d'être exposée. Sur une voix synthétique, beaucoup d'auditeurs montent à un virgule deux ou un virgule cinq sans perte de compréhension, parce que le débit par défaut est calibré pour être confortable au premier essai plutôt qu'à la dixième heure d'écoute.",
			"Le suivi visuel du segment en cours change également l'expérience. Voir la phrase prononcée surlignée dans le texte permet de raccrocher après une distraction, et transforme l'écoute passive en lecture accompagnée — ce qui est exactement ce que font les liseuses vocales spécialisées.",
			"Il reste une réserve. Les voix disponibles dépendent du système et du navigateur, ce qui rend l'expérience inégale : excellente sur un téléphone récent, sensiblement plus pauvre sur un poste de travail ancien. Un lecteur honnête doit laisser choisir la voix plutôt que d'en imposer une.",
			CLOSING[1]
		]
	},
	{
		id: 'article-8',
		feed_id: 'feed-canal',
		author_name: 'Nadia Perrin',
		category_name: 'Usages',
		title: "Ce que l'archivage personnel dit de nous",
		summary: "Sauvegarder un article, c'est déjà formuler une intention de lecture.",
		keywords: ['archivage', 'intention', 'lecture différée'],
		published_at: '2026-08-10T20:15:00Z',
		image_hue: 220,
		paragraphs: [
			"Toutes les bibliothèques personnelles se ressemblent : un fonds soigneusement constitué et largement non lu. L'archivage numérique n'a pas inventé ce décalage, il l'a rendu mesurable, et donc culpabilisant.",
			"Il y a pourtant une lecture plus généreuse du geste. Enregistrer un article, c'est marquer un sujet comme important à un instant donné. La valeur de l'archive n'est pas dans sa consommation intégrale, elle est dans la carte des intérêts qu'elle dessine avec le temps.",
			"Un outil de lecture peut tirer parti de cette carte sans la transformer en dette. Afficher une durée totale plutôt qu'un nombre d'éléments, proposer une file qui tient dans le temps disponible : la même liste devient une invitation au lieu d'un reproche.",
			"L'archive personnelle a par ailleurs une fonction que les moteurs ne remplissent pas. Retrouver un article qu'on a lu il y a deux ans, dont on ne se rappelle ni le titre ni la source, reste laborieux sur le web ouvert et immédiat dans une collection qu'on a soi-même constituée.",
			"Encore faut-il que le contenu ait été conservé, et pas seulement son adresse. Une part significative des liens enregistrés il y a dix ans ne répond plus, et une bibliothèque de liens morts n'est pas une bibliothèque.",
			CLOSING[0]
		]
	},
	{
		id: 'article-9',
		feed_id: 'feed-sillage',
		author_name: 'Yann Delcourt',
		category_name: 'Méthode',
		title: 'Cartographier ses sources en dix minutes',
		summary: 'Méthode simple pour auditer ses flux et couper les doublons.',
		keywords: ['sources', 'audit', 'organisation'],
		published_at: '2026-08-10T08:00:00Z',
		image_hue: 175,
		paragraphs: [
			"Une liste de flux vieillit mal. On s'abonne par curiosité, on ne se désabonne presque jamais, et le volume finit par rendre l'ensemble illisible. Un audit annuel suffit à remettre la liste d'aplomb.",
			"La méthode tient en trois colonnes : combien d'articles cette source publie-t-elle par semaine, combien en ai-je ouverts, combien en ai-je terminés. Le rapport entre la première et la troisième colonne suffit à trancher, sans qu'aucun jugement éditorial soit nécessaire.",
			"Les doublons méritent un traitement à part. Deux agrégateurs qui reprennent les mêmes dépêches occupent deux fois la place pour une seule information : garder la source primaire et couper le relais gagne du volume sans rien perdre.",
			"Reste un cas particulier, les sources à très faible fréquence. Une publication mensuelle disparaît dans un flux chronologique alors qu'elle est souvent la mieux écrite : elle gagne à être rangée dans un dossier à part, consulté délibérément.",
			"L'organisation en dossiers demande elle aussi une révision. Les arborescences profondes vieillissent mal parce qu'on oublie où l'on a rangé quoi ; une dizaine de dossiers thématiques à plat se retiennent, une hiérarchie à trois niveaux ne se retient pas.",
			"Un dernier réflexe utile : conserver la liste au format OPML après chaque audit. C'est le seul format que tous les lecteurs acceptent, et c'est ce qui rend le changement d'outil possible sans tout reconstruire à la main.",
			CLOSING[1]
		]
	},
	{
		id: 'article-10',
		feed_id: 'feed-atelier',
		author_name: 'Marc Estève',
		category_name: 'Édition',
		title: 'Les kiosques numériques réinventent la une',
		summary: 'La hiérarchie visuelle de la presse papier revient dans les interfaces de lecture.',
		keywords: ['kiosque', 'hiérarchie', 'une'],
		published_at: '2026-08-09T17:25:00Z',
		image_hue: 15,
		paragraphs: [
			"Une une de journal fait un travail que peu d'interfaces numériques tentent encore : elle hiérarchise. Un article domine, deux le suivent, le reste s'aligne. En une seconde, le lecteur sait ce que la rédaction juge important.",
			"Les listes chronologiques ont effacé cette hiérarchie au nom de la neutralité. La neutralité est un leurre : l'ordre chronologique privilégie simplement ce qui vient d'être publié, et la fraîcheur n'a jamais été un critère d'importance.",
			"Rendre la hiérarchie explicite, c'est accepter d'assumer un score et de le montrer. Afficher la pertinence estimée à côté d'un article a un mérite que l'opacité n'a pas : le lecteur peut être en désaccord, et le dire.",
			"La une papier avait un autre avantage, rarement transposé : elle était finie. Douze articles, pas plus, et le lecteur savait qu'il en avait fait le tour. Une grille numérique peut reproduire cette finitude en assumant de ne montrer qu'une sélection du jour.",
			"Le risque de la mise en scène est connu : à force de hiérarchiser, on finit par imposer un point de vue. La différence tient à la réversibilité, un lecteur qui peut réordonner, filtrer ou ignorer le classement garde la main, ce que la une papier n'a jamais permis.",
			CLOSING[0]
		]
	},
	{
		id: 'article-11',
		feed_id: 'feed-fibre',
		author_name: 'Claire Baudet',
		category_name: 'Audio',
		title: 'Écouter sa veille en marchant',
		summary: "Le format audio change la façon dont on hiérarchise sa file de lecture.",
		keywords: ['audio', 'playlist', 'mobilité'],
		published_at: '2026-08-09T07:30:00Z',
		image_hue: 320,
		paragraphs: [
			"Écouter n'est pas lire au ralenti. Le format impose ses contraintes : on ne revient pas en arrière aussi facilement, on ne survole pas, et un texte dense devient vite épuisant à suivre sans support visuel.",
			"Cette contrainte a une conséquence utile sur la sélection. Les articles qui passent bien à l'oreille sont ceux dont la structure est claire, avec des transitions marquées. Constituer une file d'écoute revient donc à repérer les textes les mieux construits.",
			"La durée devient alors l'unité de mesure naturelle. Une file de vingt-cinq minutes correspond à un trajet, pas à un nombre d'articles. Afficher le total d'une playlist en minutes plutôt qu'en éléments change la façon dont on la remplit.",
			"L'enchaînement automatique pose une question de conception rarement tranchée. Faut-il annoncer le titre suivant avant de le lire ? Sans annonce, on perd le fil et on ne sait plus de quel article vient le propos ; avec annonce, l'écoute est hachée par une voix qui récite des métadonnées.",
			"Le compromis praticable consiste à annoncer seulement le passage d'un article à l'autre, brièvement, et à laisser le reste couler. C'est ce que font les podcasts qui enchaînent des chroniques, et l'oreille s'y retrouve sans effort.",
			"Reste la reprise. Une file d'écoute interrompue au milieu d'un article doit reprendre au même endroit, pas au début du fichier, sinon l'auditeur réécoute trois minutes à chaque trajet et finit par abandonner le format.",
			CLOSING[1]
		]
	},
	{
		id: 'article-12',
		feed_id: 'feed-preprint',
		author_name: 'Sofia Ferreira',
		category_name: 'Recherche',
		title: "Les corpus scientifiques ouverts changent d'échelle",
		summary: 'Les dépôts ouverts publient plus vite que les revues ne relisent.',
		keywords: ['science ouverte', 'préprint', 'relecture'],
		published_at: '2026-08-08T14:00:00Z',
		image_hue: 195,
		paragraphs: [
			"Le dépôt de préprints a cessé d'être une pratique marginale. Dans plusieurs disciplines, la version déposée est devenue la version lue, et la publication en revue n'intervient que des mois plus tard, à des fins de carrière plus que de diffusion.",
			"Ce déplacement transfère au lecteur une part du travail de tri qui incombait à la relecture par les pairs. Suivre un dépôt sans filtre revient à recevoir plusieurs centaines de textes par semaine, dont l'immense majorité est hors sujet pour n'importe quel lecteur donné.",
			"C'est le cas d'usage où un score de pertinence appris devient franchement utile : non pas pour juger de la qualité scientifique, dont aucun modèle local ne peut décider, mais pour ramener un flux ingérable à une taille lisible.",
			"La prudence s'impose sur un point : un texte non relu reste un texte non relu. Un lecteur qui abaisse le coût d'accès à ces corpus doit en rappeler le statut, sous peine de faire passer une hypothèse pour un résultat.",
			"Les dépôts eux-mêmes ont commencé à structurer cette information. Version déposée, version révisée, lien vers la publication finale lorsqu'elle existe : ces métadonnées circulent dans les flux et peuvent être affichées, à condition que l'outil de lecture accepte de les transporter.",
			"C'est un cas d'usage qui pousse un lecteur généraliste dans ses retranchements. Un flux scientifique n'a pas la même granularité qu'un flux d'actualité : les auteurs sont nombreux, les titres longs, les résumés structurés, et l'affichage conçu pour un billet de blog rend mal ces contenus.",
			"La bonne nouvelle est que le résumé automatique fonctionne particulièrement bien sur ces textes, précisément parce qu'ils sont déjà écrits selon un plan rigide dont la première partie annonce le contenu.",
			CLOSING[0]
		]
	}
];

export const SEED_PLAYLISTS: { id: string; name: string; article_ids: string[] }[] = [
	{
		id: 'playlist-weekend',
		name: 'À lire ce weekend',
		article_ids: ['article-1', 'article-4', 'article-6', 'article-10']
	},
	{
		id: 'playlist-veille',
		name: 'Veille techno',
		article_ids: ['article-2', 'article-3', 'article-7']
	},
	{
		id: 'playlist-longue',
		name: 'Lecture longue',
		article_ids: ['article-5', 'article-9', 'article-12']
	}
];

/** Articles the demo starts with already saved, favourited or read. */
export const SEED_SAVED = ['article-3', 'article-8', 'article-11'];
export const SEED_FAVORITES = ['article-1', 'article-7'];
export const SEED_READ = ['article-6', 'article-10'];
/**
 * A handful of votes already cast, so the relevance scores are not all sitting at the neutral 50
 * when the demo opens. They feed the same accumulation the real backend does.
 */
export const SEED_LIKED = ['article-1', 'article-7', 'article-11'];
export const SEED_DISLIKED = ['article-9'];

/**
 * The same shape as the catalogue bundled with the backend, trimmed to a page's worth. These are
 * real public feeds: the demo can't fetch them, but the urls have to be believable enough to judge
 * the screen.
 */
export const SEED_DISCOVER: {
	title: string;
	url: string;
	site_url: string;
	description: string;
	language: string;
	topics: string[];
}[] = [
	{
		title: 'Next',
		url: 'https://next.ink/feed/',
		site_url: 'https://next.ink',
		description: 'Informatique, logiciel libre et politiques du numérique.',
		language: 'fr',
		topics: ['outils', 'vie privée', 'auto-hébergement']
	},
	{
		title: 'LinuxFr.org',
		url: 'https://linuxfr.org/news.atom',
		site_url: 'https://linuxfr.org',
		description: 'Actualité du logiciel libre, écrite par ses utilisateurs.',
		language: 'fr',
		topics: ['auto-hébergement', 'rss', 'outils']
	},
	{
		title: 'Étapes',
		url: 'https://etapes.com/feed/',
		site_url: 'https://etapes.com',
		description: 'Design graphique, typographie et culture visuelle.',
		language: 'fr',
		topics: ['typographie', 'composition', 'lisibilité']
	},
	{
		title: 'CNRS Le Journal',
		url: 'https://lejournal.cnrs.fr/rss',
		site_url: 'https://lejournal.cnrs.fr',
		description: 'La recherche française racontée par le CNRS.',
		language: 'fr',
		topics: ['recherche', 'science ouverte', 'préprint']
	},
	{
		title: 'Julia Evans',
		url: 'https://jvns.ca/atom.xml',
		site_url: 'https://jvns.ca',
		description: 'Systems and networking, explained from first principles.',
		language: 'en',
		topics: ['outils', 'algorithmes']
	},
	{
		title: 'Quanta Magazine',
		url: 'https://api.quantamagazine.org/feed/',
		site_url: 'https://www.quantamagazine.org',
		description: 'Mathematics, physics and computer science, at length.',
		language: 'en',
		topics: ['recherche', 'algorithmes']
	},
	{
		title: 'Low-tech Magazine',
		url: 'https://solar.lowtechmagazine.com/feeds/all-en.atom.xml',
		site_url: 'https://solar.lowtechmagazine.com',
		description: 'Energy, sobriety and technologies that last.',
		language: 'en',
		topics: ['web lent', 'attention', 'usages']
	},
	{
		title: 'CSS-Tricks',
		url: 'https://css-tricks.com/feed/',
		site_url: 'https://css-tricks.com',
		description: 'Front-end techniques, layout and browser behaviour.',
		language: 'en',
		topics: ['interface', 'grille', 'composition']
	}
];
