/**
 * The floor the API enforces on every password it writes (`MIN_PASSWORD_LENGTH`, backend side).
 * Repeated here so a form can say what is wrong before a round trip, never to replace that check.
 */
export const MIN_PASSWORD_LENGTH = 8;
