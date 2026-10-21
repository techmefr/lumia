export interface NewsletterInboxStatus {
	active: boolean;
	created_at: string | null;
}

export interface NewsletterInboxCreated {
	token: string;
	created_at: string;
}
