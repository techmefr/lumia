import { mount } from 'svelte';
import '$technical/styles/app.css';
import { getExtension } from '$technical/browser/extension-api';
import Settings from '$domain/settings/settings.svelte';

mount(Settings, { target: document.getElementById('app')!, props: { extension: getExtension() } });
