import type {
	ArticleDetail,
	ArticleSummary,
	Feed,
	Folder,
	InstanceSettings,
	Me,
	PlaylistDetail,
	PlaylistSummary
} from '@lumia/core';

export function articleSummary(id: string, overrides: Partial<ArticleSummary> = {}): ArticleSummary {
	return {
		id,
		feed_id: 'feed-1',
		author_id: null,
		author_name: null,
		category_id: null,
		category_name: null,
		source_label: 'Atelier Papier',
		title: `Titre ${id}`,
		url: `https://example.test/${id}`,
		summary: null,
		image_url: null,
		published_at: '2026-08-09T08:30:00Z',
		reading_minutes: 4,
		read: false,
		scroll_progress: 0,
		relevance_score: 50,
		...overrides
	};
}

export function articleDetail(id: string, overrides: Partial<ArticleDetail> = {}): ArticleDetail {
	return {
		...articleSummary(id),
		content: '<p>Le corps de l article.</p>',
		keywords: [],
		...overrides
	};
}

export function folder(id: string, name = `Dossier ${id}`): Folder {
	return { id, name };
}

export function feed(id: string, overrides: Partial<Feed> = {}): Feed {
	return {
		id,
		folder_id: null,
		source_type: 'miniflux',
		external_feed_id: `ext-${id}`,
		title: `Flux ${id}`,
		url: `https://example.test/${id}.xml`,
		error_count: 0,
		error_reason: null,
		error_since: null,
		refresh_interval_minutes: null,
		last_refreshed_at: null,
		...overrides
	};
}

export function playlistSummary(
	id: string,
	overrides: Partial<PlaylistSummary> = {}
): PlaylistSummary {
	return { id, name: `Playlist ${id}`, item_count: 2, total_reading_minutes: 8, ...overrides };
}

export function playlistDetail(
	id: string,
	articles: ArticleSummary[] = [],
	overrides: Partial<PlaylistDetail> = {}
): PlaylistDetail {
	return { id, name: `Playlist ${id}`, articles, ...overrides };
}

export function me(overrides: Partial<Me> = {}): Me {
	return {
		id: 'user-1',
		email: 'reader@example.test',
		username: 'camille',
		role: 'member',
		password_set: true,
		theme: 'light',
		orbit_position: 'left',
		font_base_size: 16,
		preferred_language: 'fr',
		ai_provider: null,
		ai_endpoint_url: null,
		ai_model: null,
		ai_api_key_set: false,
		translation_provider: null,
		...overrides
	} as Me;
}

export function instanceSettings(overrides: Partial<InstanceSettings> = {}): InstanceSettings {
	return { max_accounts: 10, disk_quota_mb: 500, access_mode: 'on_approval', account_count: 1, ...overrides };
}
