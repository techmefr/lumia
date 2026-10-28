import { mount } from 'svelte';
import '$technical/styles/app.css';
import { getExtension } from '$technical/browser/extension-api';
import Popup from './popup.svelte';

mount(Popup, { target: document.getElementById('app')!, props: { extension: getExtension() } });
