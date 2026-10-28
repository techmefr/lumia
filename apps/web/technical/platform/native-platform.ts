import { Capacitor } from '@capacitor/core';

export function isNativePlatform(): boolean {
	return Capacitor.isNativePlatform();
}
