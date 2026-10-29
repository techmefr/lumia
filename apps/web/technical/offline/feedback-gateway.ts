import { toast } from '@lumia/ui';
import { lumia } from '../api/client';
import { t } from '../i18n/i18n.svelte';
import { connectivity } from './connectivity.svelte';
import { createFeedbackSync } from './feedback-sync';
import { ownerFromToken } from './session-owner';

export const feedbackGateway = createFeedbackSync(
	(articleId, update) => lumia.recommendation.sendFeedback(articleId, update),
	() => connectivity.online,
	() => ownerFromToken(lumia.tokenStore?.getAccessToken() ?? null),
	(_articleId, reason) => {
		if (reason !== 'foreign') toast(t('offline.feedbackDropped'), { tone: 'destructive' });
	}
);
