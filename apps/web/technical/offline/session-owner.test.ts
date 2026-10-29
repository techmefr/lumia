import { describe, expect, it } from 'vitest';
import { ownerFromToken } from './session-owner';

function token(claims: unknown): string {
	return `h.${btoa(JSON.stringify(claims)).replace(/\+/g, '-').replace(/\//g, '_')}.s`;
}

describe('ownerFromToken', () => {
	it('reads the subject of the access token', () => {
		expect(ownerFromToken(token({ sub: 'user-1' }))).toBe('user-1');
	});

	it('gives nobody for a missing or unreadable token', () => {
		expect(ownerFromToken(null)).toBeNull();
		expect(ownerFromToken('opaque')).toBeNull();
		expect(ownerFromToken('a.!!.c')).toBeNull();
		expect(ownerFromToken(token({ sub: 4 }))).toBeNull();
	});
});
