import { LocalNotifications } from '@capacitor/local-notifications';

export type NativePermission = 'default' | 'granted' | 'denied';

const NOTIFICATION_ID = 1;

function toPermission(receive: string): NativePermission {
	if (receive === 'granted') return 'granted';
	if (receive === 'denied') return 'denied';
	return 'default';
}

export async function checkNativePermission(): Promise<NativePermission> {
	return toPermission((await LocalNotifications.checkPermissions()).display);
}

export async function requestNativePermission(): Promise<NativePermission> {
	return toPermission((await LocalNotifications.requestPermissions()).display);
}

export async function showNativeNotification(title: string, body: string): Promise<void> {
	await LocalNotifications.schedule({ notifications: [{ id: NOTIFICATION_ID, title, body }] });
}
