import { lumia } from '../api/client';
import { connectivity } from './connectivity.svelte';
import { createFeedbackSync } from './feedback-sync';

export const feedbackGateway = createFeedbackSync(
	(articleId, update) => lumia.recommendation.sendFeedback(articleId, update),
	() => connectivity.online
);
