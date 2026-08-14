/**
 * The reference catalogue. Its keys define `MessageKey`, so every other locale is checked against
 * it at compile time and a forgotten string is a type error rather than a blank label.
 *
 * `{name}` placeholders are substituted at call time. Keys are grouped by screen, then by role.
 */
export const fr = {
	'nav.articles': 'Articles',
	'nav.etincelle': "L'Étincelle",
	'nav.feeds': 'Mes flux',
	'nav.readLater': 'À lire',
	'nav.playlists': 'Playlists',
	'nav.settings': 'Réglages',
	'nav.favorites': 'Favoris',
	'nav.logout': 'Déconnexion',
	'nav.main': 'Navigation principale',
	'nav.mobile': 'Navigation mobile',
	'nav.skipToContent': 'Aller au contenu',

	'common.save': 'Enregistrer',
	'common.saving': 'Enregistrement…',
	'common.cancel': 'Annuler',
	'common.add': 'Ajouter',
	'common.adding': 'Ajout…',
	'common.delete': 'Supprimer',
	'common.rename': 'Renommer',
	'common.close': 'Fermer',
	'common.open': 'Ouvrir',
	'common.retry': 'Réessayer',
	'common.loading': 'Chargement…',
	'common.minutes': '{count} min',
	'common.none': 'Aucun.',

	'login.tagline': 'Connecte-toi pour retrouver tes flux.',
	'login.email': 'Email',
	'login.password': 'Mot de passe',
	'login.submit': 'Se connecter',
	'login.submitting': 'Connexion…',
	'login.badCredentials': 'Email ou mot de passe incorrect.',
	'login.failed': 'Connexion impossible.',
	'login.firstRun': 'Premier lancement ?',
	'login.createAdmin': 'Créer le compte administrateur',

	'settings.title': 'Réglages',
	'settings.theme': 'Thème',
	'settings.themeLight': 'Clair',
	'settings.themeDark': 'Sombre',
	'settings.accent': 'Couleur principale',
	'settings.language': 'Langue de l’interface',
	'settings.languageHint':
		"Change la langue de l'application. La langue de lecture des articles se règle plus bas, avec la traduction.",
	'settings.fontPair': 'Paire de polices',
	'settings.fontPairHint':
		"Un serif pour les titres, un sans pour le texte courant. Les quatre paires sont servies par ton instance : rien n'est chargé depuis un tiers.",
	'settings.textSize': 'Taille du texte',
	'settings.textSizeHint':
		'La hiérarchie visuelle (titres, texte, légendes) garde toujours les mêmes proportions — seule la taille globale change.',
	'settings.comfort': 'Confort de lecture',
	'settings.comfortHint':
		"Des lignes plus aérées et un peu plus d'espace entre les mots, pour ne pas perdre sa ligne.",
	'settings.comfortOn': 'Activé',
	'settings.comfortOff': 'Désactivé',
	'settings.previewTitle': 'Aperçu du titre',
	'settings.previewBody':
		'Un texte de résumé, pour vérifier que la hiérarchie reste lisible à toutes les tailles.',
	'settings.previewCaption': 'Légende discrète',

	'settings.scale.sm': 'Petit',
	'settings.scale.md': 'Normal',
	'settings.scale.lg': 'Grand',
	'settings.scale.xl': 'Très grand',
	'settings.scale.xxl': 'Maximum',

	'notifications.title': 'Notifications',
	'notifications.intro':
		"Lumia interroge ton instance à intervalle régulier tant qu'un onglet reste ouvert, et te prévient quand des articles non lus arrivent. Rien ne passe par un service de push tiers : aucun identifiant d'appareil ne quitte ton navigateur.",
	'notifications.unsupported': 'Ce navigateur ne propose pas de notifications.',
	'notifications.denied':
		'Les notifications sont bloquées pour ce site. À réautoriser dans les réglages du navigateur.',
	'notifications.enable': 'Activer les notifications',
	'notifications.disable': 'Désactiver',
	'notifications.enabled': 'Notifications activées.',
	'notifications.refused': "Le navigateur n'a pas accordé les notifications.",
	'notifications.frequency': 'Fréquence de vérification',
	'notifications.everyMinutes': 'Toutes les {count} min',
	'notifications.everyHours': 'Toutes les {count} h',
	'notifications.threshold': "À partir de combien d'articles",
	'notifications.thresholdFirst': 'Dès le premier',
	'notifications.thresholdCount': '{count} articles',
	'notifications.thresholdHint': "Un seul article n'est pas toujours une raison d'être interrompu.",
	'notifications.quietHours': 'Heures silencieuses',
	'notifications.quietFrom': 'De',
	'notifications.quietTo': 'à',
	'notifications.quietHint':
		'Deux heures identiques désactivent la plage. La plage peut passer minuit.',
	'notifications.saved': 'Réglages de notification enregistrés.',
	'notifications.newArticle': '1 nouvel article à lire',
	'notifications.newArticles': '{count} nouveaux articles à lire',

	'rules.title': 'Mots-clés mis en avant ou masqués',
	'rules.intro':
		"Une règle s'ajoute par-dessus ce que tes votes ont appris. Un terme mis en avant remonte les articles qui le mentionnent ; un terme masqué les retire des listes et de L'Étincelle. La comparaison porte sur le titre et le résumé, sans tenir compte de la casse.",
	'rules.term': 'Terme',
	'rules.termPlaceholder': 'rust, crypto, élection…',
	'rules.effect': 'Effet',
	'rules.boost': 'Mettre en avant',
	'rules.mute': 'Masquer',
	'rules.boosted': 'Mis en avant',
	'rules.muted': 'Masqués',
	'rules.tooShort': 'Il faut au moins deux caractères.',
	'rules.loadFailed': 'Impossible de charger les règles.',
	'rules.saveFailed': "La règle n'a pas pu être enregistrée.",
	'rules.deleteFailed': 'Suppression impossible.',
	'rules.boostDone': 'Terme mis en avant.',
	'rules.muteDone': 'Terme masqué.',
	'rules.removeOne': 'Supprimer la règle {term}',

	'ai.title': 'IA et traduction',
	'ai.intro':
		"Optionnel : les mots-clés et le résumé sont calculés localement. Une clé sert au résumé enrichi par un modèle et à la traduction des articles étrangers. Chaque compte pose la sienne — elle est chiffrée en base et n'est jamais renvoyée par l'API.",
	'ai.readingLanguage': 'Langue de lecture',
	'ai.readingLanguageHint':
		"Les articles publiés dans une autre langue sont traduits vers celle-ci, quand un fournisseur de traduction est configuré.",
	'ai.provider': 'Fournisseur de résumé',
	'ai.providerNone': 'Aucun — résumé local',
	'ai.providerCustom': 'Endpoint compatible OpenAI (auto-hébergé)',
	'ai.apiKey': "Clé d'API",
	'ai.keyOnFile': '— une clé est enregistrée',
	'ai.keyKeep': 'Laisser vide pour conserver la clé',
	'ai.keyHint': "La clé n'est jamais réaffichée. Pour la retirer, utilise « Supprimer la clé ».",
	'ai.model': 'Modèle',
	'ai.modelDefault': 'laisser vide = par défaut',
	'ai.endpoint': "URL de l'endpoint",
	'ai.deleteKey': 'Supprimer la clé',
	'ai.translationProvider': 'Fournisseur de traduction',
	'ai.translationNone': 'Aucun — pas de traduction',
	'ai.deeplKey': 'Clé DeepL',
	'ai.loadFailed': 'Impossible de charger tes réglages.',
	'ai.saveFailed': 'Enregistrement impossible. Vérifie la clé et réessaie.',
	'ai.saved': 'Réglages enregistrés.',
	'ai.unavailable': 'Réglages indisponibles.',
	'ai.loading': 'Chargement des réglages…',
	'ai.summaryKeyDeleted': 'Clé de résumé supprimée.',
	'ai.deeplKeyDeleted': 'Clé DeepL supprimée.'
} as const;

export type MessageKey = keyof typeof fr;
export type Catalogue = Record<MessageKey, string>;
