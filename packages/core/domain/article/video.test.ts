import { describe, expect, it } from "vitest";
import { youtubeEmbedUrl } from "./video";

describe("youtubeEmbedUrl", () => {
	it.each([
		["https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=3", "dQw4w9WgXcQ"],
		["https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"],
		["https://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"]
	])("embeds %s without cookies", (url, id) => {
		expect(youtubeEmbedUrl(url)).toBe(`https://www.youtube-nocookie.com/embed/${id}`);
	});

	it.each([
		"https://example.com/watch?v=dQw4w9WgXcQ",
		"https://www.youtube.com/@MrBeast",
		"https://www.youtube.com/watch?v=",
		"https://www.youtube.com/watch?v=a/b\"><x",
		"not a url"
	])("returns null for %s", (url) => {
		expect(youtubeEmbedUrl(url)).toBeNull();
	});
});
