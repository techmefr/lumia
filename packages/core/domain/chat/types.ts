export type ChatRole = 'user' | 'assistant';
export type ChatAction = 'summarize' | 'explain' | 'diagram';

export interface ChatMessage {
	id: string;
	role: ChatRole;
	content: string;
	/** Set on the reader turn that came from a quick action rather than from typed text. */
	action: ChatAction | null;
	/** The text the reader had selected when asking, quoted to the model with the question. */
	passage: string | null;
	created_at: string;
}

export type ChatRequest =
	| { message: string; passage?: string }
	| { action: 'summarize' | 'explain'; passage?: string }
	| { action: 'diagram' };
