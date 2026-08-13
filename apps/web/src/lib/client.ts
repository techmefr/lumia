import { createLumiaClient } from '@lumia/core';

export const lumia = createLumiaClient(import.meta.env.VITE_API_BASE_URL);
