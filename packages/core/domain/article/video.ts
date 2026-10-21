const YOUTUBE_HOSTS = new Set(["youtube.com", "www.youtube.com", "m.youtube.com"]);
const VIDEO_ID = /^[\w-]{6,20}$/;

export function youtubeVideoId(url: string): string | null {
	let parsed: URL;
	try {
		parsed = new URL(url);
	} catch {
		return null;
	}
	const id =
		parsed.hostname === "youtu.be"
			? parsed.pathname.slice(1)
			: YOUTUBE_HOSTS.has(parsed.hostname) && parsed.pathname === "/watch"
				? parsed.searchParams.get("v")
				: null;
	return id !== null && VIDEO_ID.test(id) ? id : null;
}

export function youtubeEmbedUrl(url: string): string | null {
	const id = youtubeVideoId(url);
	return id === null ? null : `https://www.youtube-nocookie.com/embed/${id}`;
}
