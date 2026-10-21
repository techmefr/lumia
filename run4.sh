cd ~/perso/lumia-wt/related
G="git -c credential.helper=!gh\ auth\ git-credential"
git add -A && git commit -q -m "feat(article): suggest related articles at the end of an article" && \
git -c credential.helper='!gh auth git-credential' fetch -q origin main && git rebase origin/main 2>&1 | tail -3
git -c credential.helper='!gh auth git-credential' push -q -u origin feat/related-articles 2>&1 | tail -2
cat > /tmp/body78.txt <<'B'
Adds GET /articles/{id}/related and a "Related articles" section at the bottom of the article page, rendered with the existing article cards.

Related articles are ranked in a single SQL query from what already exists: the summed weight of shared keywords, plus a bonus for the same author and the same category. Only the reader's own unread articles are considered, anything sharing the canonical url (a republished duplicate) is dropped, and the result is capped at 5. A foreign or unknown article answers 404. The section stays hidden when nothing matches or the lookup fails. The core api and the demo client implement the new call, and the label is translated in all 10 locales.

What was cut: the issue asks for the result to be precomputed at enrichment time and for content proximity. This computes it per request, which is a single indexed query, and avoids a migration and new storage. Full-text proximity on search_vector is left out for now.

Closes #78
B
gh pr create -R techmefr/lumia --base main --title "feat(article): related articles on the article page" --body-file /tmp/body78.txt
