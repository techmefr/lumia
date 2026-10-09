/// <reference types="@sveltejs/kit" />
/// <reference lib="webworker" />

// This is Lumia's first service worker, and its job stops at the app shell: get the SPA to boot
// with no network, so a saved list that was already fetched has a page to render into. It never
// touches an API response — see the `fetch` handler below for why — and it never touches article
// bodies either: those are opted into offline reading explicitly and live in IndexedDB
// (domain/offline), read directly by the app rather than served through this worker.

import { base, build, files, version } from '$service-worker';

declare const self: ServiceWorkerGlobalScope;

const CACHE_NAME = `lumia-shell-${version}`;
const SHELL_ROOT = `${base}/`;
const APP_SHELL = [SHELL_ROOT, ...build, ...files];

self.addEventListener('install', (event) => {
	event.waitUntil(
		caches
			.open(CACHE_NAME)
			.then((cache) => cache.addAll(APP_SHELL))
			.then(() => self.skipWaiting())
	);
});

self.addEventListener('activate', (event) => {
	event.waitUntil(
		caches
			.keys()
			.then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
			.then(() => self.clients.claim())
	);
});

self.addEventListener('fetch', (event) => {
	const { request } = event;
	if (request.method !== 'GET') return;

	const url = new URL(request.url);
	if (url.origin !== self.location.origin) return;

	// The precached shell: serve from cache first, since these files are content-hashed and never
	// change under a given `version`.
	if (APP_SHELL.includes(url.pathname)) {
		event.respondWith(caches.match(request).then((cached) => cached ?? fetch(request)));
		return;
	}

	// Everything else — API calls, article images, feed icons — is deliberately left to the network.
	// A cached `/articles` list would report unread counts and a saved list that are no longer true,
	// which is worse than having no offline support at all.
	if (request.mode !== 'navigate') return;

	// A route the SPA renders client-side (e.g. an article page): let the network try first, and
	// only fall back to the cached shell once it's clear there is none. `adapter-static`'s fallback
	// build means the shell alone is enough for the router to take over from there.
	event.respondWith(
		fetch(request).catch(async () => (await caches.match(SHELL_ROOT)) ?? Response.error())
	);
});
