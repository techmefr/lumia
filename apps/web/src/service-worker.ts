/// <reference types="@sveltejs/kit" />
/// <reference no-default-lib="true" />
/// <reference lib="esnext" />
/// <reference lib="webworker" />
import { assets, immutable } from "$app/manifest";
import {
  IMAGE_CACHE_NAME,
  SYNC_IMAGES_MESSAGE,
  acceptedImageUrls,
  isTrustedSource,
} from "$technical/offline/image-cache";

declare const self: ServiceWorkerGlobalScope;

const base = new URL(self.registration.scope).pathname.replace(/\/$/, "");
const toShellUrl = (entry: { path: string }): string =>
  `${base}/${entry.path.replace(/^\//, "")}`;

const SHELL_VERSION = [
  ...[...immutable, ...assets]
    .map((entry) => entry.path)
    .sort()
    .join("|"),
]
  .reduce((hash, char) => (Math.imul(hash, 31) + char.charCodeAt(0)) >>> 0, 7)
  .toString(36);

const SHELL_CACHE = `lumia-shell-${SHELL_VERSION}`;
const SHELL_FALLBACK = `${base}/index.html`;
const SHELL_ASSETS = new Set([...immutable, ...assets].map(toShellUrl));

async function fetchOpaqueImage(url: string): Promise<Response | null> {
  try {
    return await fetch(url, { mode: "no-cors" });
  } catch {
    return null;
  }
}

async function fetchImage(url: string): Promise<Response | null> {
  try {
    const response = await fetch(url, { mode: "cors" });
    if (response.ok) return response;
  } catch {
    return fetchOpaqueImage(url);
  }
  return fetchOpaqueImage(url);
}

async function syncImages(urls: string[]): Promise<void> {
  const cache = await caches.open(IMAGE_CACHE_NAME);
  const wanted = new Set(urls);
  for (const request of await cache.keys()) {
    if (!wanted.has(request.url)) await cache.delete(request);
  }
  for (const url of wanted) {
    if (await cache.match(url)) continue;
    const response = await fetchImage(url);
    if (response) await cache.put(url, response);
  }
}

async function respondToNavigation(request: Request): Promise<Response> {
  try {
    return await fetch(request);
  } catch {
    const cached = await caches.match(SHELL_FALLBACK);
    return cached ?? Response.error();
  }
}

async function respondToAsset(request: Request): Promise<Response> {
  const cached = await caches.match(request);
  return cached ?? fetch(request);
}

async function respondToImage(request: Request): Promise<Response> {
  const cached = await caches.match(request, { cacheName: IMAGE_CACHE_NAME });
  return cached ?? fetch(request);
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      .then((cache) => cache.addAll([...SHELL_ASSETS, SHELL_FALLBACK]))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((names) =>
        Promise.all(
          names
            .filter(
              (name) => name.startsWith("lumia-shell-") && name !== SHELL_CACHE,
            )
            .map((name) => caches.delete(name)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("message", (event) => {
  const data = event.data as { type?: string; urls?: string[] } | undefined;
  if (!isTrustedSource(event.source as { url?: unknown } | null, self.location.origin)) return;
  if (data?.type === SYNC_IMAGES_MESSAGE && Array.isArray(data.urls)) {
    event.waitUntil(syncImages(acceptedImageUrls(data.urls)));
  }
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);

  if (request.mode === "navigate" && url.origin === self.location.origin) {
    event.respondWith(respondToNavigation(request));
    return;
  }
  if (url.origin === self.location.origin && SHELL_ASSETS.has(url.pathname)) {
    event.respondWith(respondToAsset(request));
    return;
  }
  if (request.destination === "image") {
    event.respondWith(respondToImage(request));
  }
});
