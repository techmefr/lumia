import { getExtension } from '$technical/browser/extension-api';
import { registerBackground } from './handlers';

registerBackground(getExtension());
