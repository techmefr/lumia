<script lang="ts">
	import { onMount } from 'svelte';
	import {
		ApiError,
		type PlaylistMemberRole,
		type PlaylistMembers,
		type PlaylistRole
	} from '@lumia/core';
	import { Button, Card, CardContent, CardHeader, CardTitle, Input, Label, toast, Icon } from '@lumia/ui';
	import { UserAdd01Icon, UserRemove01Icon } from '@hugeicons/core-free-icons';
	import { lumia } from '$technical/api/client';
	import { t, type MessageKey } from '$technical/i18n/i18n.svelte';

	interface Props {
		playlistId: string;
		role: PlaylistRole;
		onleave?: () => void;
	}

	let { playlistId, role, onleave }: Props = $props();

	const ROLE_LABELS: Record<PlaylistMemberRole, MessageKey> = {
		editor: 'playlists.roleEditor',
		viewer: 'playlists.roleViewer'
	};

	let sharing = $state<PlaylistMembers | null>(null);
	let myId = $state<string | null>(null);
	let email = $state('');
	let newRole = $state<PlaylistMemberRole>('viewer');
	let error = $state<MessageKey | null>(null);

	const isOwner = $derived(role === 'owner');

	async function load() {
		try {
			[sharing, myId] = await Promise.all([
				lumia.playlist.listMembers(playlistId),
				lumia.user.getMe().then((me) => me.id)
			]);
		} catch {
			error = 'playlists.sharingFailed';
		}
	}

	async function share(event: SubmitEvent) {
		event.preventDefault();
		const address = email.trim();
		if (!address) return;
		error = null;
		try {
			sharing = await lumia.playlist.shareWith(playlistId, address, newRole);
			email = '';
			toast(t('playlists.sharingAdded', { name: address }));
		} catch (err) {
			error =
				err instanceof ApiError && err.status === 404
					? 'playlists.sharingUnknownUser'
					: err instanceof ApiError && err.status === 422
						? 'playlists.sharingOwnerSelf'
						: 'playlists.sharingFailed';
		}
	}

	async function remove(userId: string, username: string) {
		error = null;
		try {
			await lumia.playlist.removeMember(playlistId, userId);
			if (userId === myId) {
				toast(t('playlists.leftToast'));
				onleave?.();
				return;
			}
			toast(t('playlists.sharingRemoved', { name: username }));
			await load();
		} catch {
			error = 'playlists.sharingFailed';
		}
	}

	onMount(() => void load());
</script>

<Card data-test-playlist-sharing>
	<CardHeader>
		<CardTitle>{t('playlists.sharingTitle')}</CardTitle>
	</CardHeader>
	<CardContent class="flex flex-col gap-4">
		{#if sharing}
			<p class="text-sm text-muted-foreground">
				{t('playlists.sharingOwner', { name: sharing.owner_name })}
			</p>

			{#if sharing.members.length === 0}
				<p class="text-sm text-muted-foreground">{t('playlists.sharingNoMembers')}</p>
			{:else}
				<ul class="flex flex-col gap-2">
					{#each sharing.members as member (member.user_id)}
						<li data-test-member={member.user_id} class="flex items-center justify-between gap-3">
							<span class="flex min-w-0 flex-col">
								<span class="truncate text-sm font-medium">{member.username}</span>
								<span class="text-xs text-muted-foreground">{t(ROLE_LABELS[member.role])}</span>
							</span>
							{#if isOwner}
								<Button
									data-test-remove-member={member.user_id}
									size="sm"
									variant="ghost"
									onclick={() => remove(member.user_id, member.username)}
								>
									<Icon icon={UserRemove01Icon} class="size-4" />
									<span class="sr-only">
										{t('playlists.sharingRemove', { name: member.username })}
									</span>
								</Button>
							{/if}
						</li>
					{/each}
				</ul>
			{/if}
		{/if}

		{#if isOwner}
			<form data-test-share-form class="flex flex-wrap items-end gap-2" onsubmit={share}>
				<div class="flex min-w-48 flex-1 flex-col gap-1.5">
					<Label for="share-email">{t('playlists.sharingEmail')}</Label>
					<Input id="share-email" type="email" bind:value={email} required />
				</div>
				<div class="flex flex-col gap-1.5">
					<Label for="share-role">{t('playlists.sharingRole')}</Label>
					<select
						data-test-share-role
						id="share-role"
						bind:value={newRole}
						class="h-9 rounded-md border border-input bg-transparent px-3 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
					>
						<option value="viewer">{t('playlists.roleViewer')}</option>
						<option value="editor">{t('playlists.roleEditor')}</option>
					</select>
				</div>
				<Button type="submit">
					<Icon icon={UserAdd01Icon} class="size-4" />
					{t('playlists.sharingSubmit')}
				</Button>
			</form>
		{:else if myId}
			<Button
				data-test-leave
				variant="outline"
				size="sm"
				class="w-fit"
				onclick={() => remove(myId!, '')}
			>
				<Icon icon={UserRemove01Icon} class="size-4" />
				{t('playlists.leave')}
			</Button>
		{/if}

		{#if error}
			<p data-test-sharing-error role="alert" class="text-sm text-destructive">{t(error)}</p>
		{/if}
	</CardContent>
</Card>
