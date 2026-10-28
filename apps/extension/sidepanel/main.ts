import { mount } from 'svelte';
import '$technical/styles/app.css';
import { getExtension } from '$technical/browser/extension-api';
import Sidepanel from './sidepanel.svelte';

mount(Sidepanel, { target: document.getElementById('app')!, props: { extension: getExtension() } });
