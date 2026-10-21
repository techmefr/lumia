export type ChatRole = 'user' | 'assistant';
export type ChatAction = 'summarize' | 'explain';

export interface ChatMessage {
	id: string;
	role: ChatRole;
	content: string;
	/** Set on the reader turn that came from a quick action rather than from typed text. */
	action: ChatAction | null;
	created_at: string;
}

export type ChatRequest = { message: string } | { action: ChatAction };
