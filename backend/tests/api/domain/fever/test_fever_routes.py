import hashlib

import httpx
import pytest

from tests.api.domain.fever.conftest import (
    ADMIN_PAYLOAD,
    add_second_reader,
    admin_headers,
    issue_api_key,
    seed,
)


async def _call(
    client: httpx.AsyncClient, api_key: str, query: str, **form: str
) -> dict[str, object]:
    response = await client.post(f"/fever/?{query}", data={"api_key": api_key, **form})
    assert response.status_code == 200
    return dict(response.json())


@pytest.fixture
async def api_key(client: httpx.AsyncClient) -> str:
    return await issue_api_key(client, await admin_headers(client))


async def test_an_unknown_key_gets_auth_zero_not_an_http_error(
    client: httpx.AsyncClient, api_key: str
) -> None:
    body = await _call(client, "0" * 32, "api&feeds")

    assert body == {"api_version": 3, "auth": 0}


async def test_a_request_without_any_key_gets_auth_zero(client: httpx.AsyncClient) -> None:
    response = await client.get("/fever/?api")

    assert response.json() == {"api_version": 3, "auth": 0}


async def test_the_md5_of_the_account_password_is_not_a_key(
    client: httpx.AsyncClient, api_key: str
) -> None:
    password_key = hashlib.md5(
        f"{ADMIN_PAYLOAD['email']}:{ADMIN_PAYLOAD['password']}".encode(), usedforsecurity=False
    ).hexdigest()

    assert (await _call(client, password_key, "api"))["auth"] == 0


async def test_a_valid_key_authenticates_over_post_and_the_bare_path(
    client: httpx.AsyncClient, api_key: str
) -> None:
    posted = await client.post("/fever", data={"api_key": api_key})

    assert posted.json()["auth"] == 1
    assert posted.json()["api_version"] == 3
    assert isinstance(posted.json()["last_refreshed_on_time"], int)


async def test_the_key_is_accepted_in_upper_case_hex(
    client: httpx.AsyncClient, api_key: str
) -> None:
    assert (await _call(client, api_key.upper(), "api"))["auth"] == 1


async def test_groups_list_folders_and_file_loose_feeds_under_one_synthetic_group(
    client: httpx.AsyncClient, api_key: str
) -> None:
    seeded = await seed()

    body = await _call(client, api_key, "api&groups")

    groups = {group["title"]: group["id"] for group in body["groups"]}  # type: ignore[attr-defined]
    assert groups["Tech"] == seeded.folder
    assert "Unfiled" in groups
    membership = {
        entry["group_id"]: entry["feed_ids"]
        for entry in body["feeds_groups"]  # type: ignore[attr-defined]
    }
    assert membership[seeded.folder] == str(seeded.filed_feed)
    assert membership[groups["Unfiled"]] == str(seeded.loose_feed)


async def test_feeds_carry_the_fields_clients_read(client: httpx.AsyncClient, api_key: str) -> None:
    seeded = await seed()

    body = await _call(client, api_key, "api&feeds")

    feeds = {feed["id"]: feed for feed in body["feeds"]}  # type: ignore[attr-defined]
    assert feeds[seeded.filed_feed]["title"] == "Filed feed"
    assert feeds[seeded.filed_feed]["url"] == "https://example.com/filed.xml"
    assert feeds[seeded.filed_feed]["is_spark"] == 0
    assert "feeds_groups" in body


async def test_favicons_and_links_are_empty_stubs(client: httpx.AsyncClient, api_key: str) -> None:
    body = await _call(client, api_key, "api&favicons&links")

    assert body["favicons"] == []
    assert body["links"] == []


async def test_items_are_mapped_from_articles(client: httpx.AsyncClient, api_key: str) -> None:
    seeded = await seed()

    body = await _call(client, api_key, "api&items")

    items: list[dict[str, object]] = body["items"]  # type: ignore[assignment]
    assert body["total_items"] == 3
    assert [item["id"] for item in items] == seeded.articles
    first = items[0]
    assert first["feed_id"] == seeded.filed_feed
    assert first["title"] == "Article 0"
    assert first["html"] == "<p>Body 0</p>"
    assert first["author"].startswith("Ada")  # type: ignore[attr-defined]
    assert first["url"] == "https://example.com/admin@example.com/0"
    assert first["is_read"] == 0
    assert first["is_saved"] == 0
    assert first["created_on_time"] == 1790856000


async def test_since_id_returns_only_newer_items_oldest_first(
    client: httpx.AsyncClient, api_key: str
) -> None:
    seeded = await seed()

    body = await _call(client, api_key, f"api&items&since_id={seeded.articles[0]}")

    assert [item["id"] for item in body["items"]] == seeded.articles[1:]  # type: ignore[attr-defined]


async def test_max_id_walks_backward_newest_first(client: httpx.AsyncClient, api_key: str) -> None:
    seeded = await seed()

    body = await _call(client, api_key, f"api&items&max_id={seeded.articles[2]}")

    assert [item["id"] for item in body["items"]] == [  # type: ignore[attr-defined]
        seeded.articles[1],
        seeded.articles[0],
    ]


async def test_max_id_zero_starts_from_the_newest(client: httpx.AsyncClient, api_key: str) -> None:
    seeded = await seed()

    body = await _call(client, api_key, "api&items&max_id=0")

    assert [item["id"] for item in body["items"]] == seeded.articles[::-1]  # type: ignore[attr-defined]


async def test_with_ids_returns_exactly_those_items(
    client: httpx.AsyncClient, api_key: str
) -> None:
    seeded = await seed()
    wanted = f"{seeded.articles[2]},{seeded.articles[0]}"

    body = await _call(client, api_key, f"api&items&with_ids={wanted}")

    assert sorted(item["id"] for item in body["items"]) == sorted(  # type: ignore[attr-defined]
        [seeded.articles[0], seeded.articles[2]]
    )


async def test_a_page_holds_at_most_fifty_items(client: httpx.AsyncClient, api_key: str) -> None:
    await seed(count=55)

    body = await _call(client, api_key, "api&items")

    assert len(body["items"]) == 50  # type: ignore[arg-type]
    assert body["total_items"] == 55


async def test_unread_and_saved_ids_follow_the_marks(
    client: httpx.AsyncClient, api_key: str
) -> None:
    seeded = await seed()
    await _call(client, api_key, f"api&mark=item&as=read&id={seeded.articles[0]}")
    await _call(client, api_key, f"api&mark=item&as=saved&id={seeded.articles[1]}")

    body = await _call(client, api_key, "api&unread_item_ids&saved_item_ids")

    assert body["unread_item_ids"] == f"{seeded.articles[1]},{seeded.articles[2]}"
    assert body["saved_item_ids"] == str(seeded.articles[1])


async def test_marking_an_item_unread_and_unsaved_reverses_it(
    client: httpx.AsyncClient, api_key: str
) -> None:
    seeded = await seed()
    target = seeded.articles[0]
    await _call(client, api_key, f"api&mark=item&as=read&id={target}")
    await _call(client, api_key, f"api&mark=item&as=saved&id={target}")
    await _call(client, api_key, f"api&mark=item&as=unread&id={target}")
    await _call(client, api_key, f"api&mark=item&as=unsaved&id={target}")

    body = await _call(client, api_key, "api&unread_item_ids&saved_item_ids")

    assert str(target) in str(body["unread_item_ids"]).split(",")
    assert body["saved_item_ids"] == ""


async def test_marks_sent_in_the_form_body_work_too(
    client: httpx.AsyncClient, api_key: str
) -> None:
    seeded = await seed()

    await _call(client, api_key, "api", mark="item", **{"as": "read"}, id=str(seeded.articles[0]))

    body = await _call(client, api_key, "api&items")
    assert body["items"][0]["is_read"] == 1  # type: ignore[index]


async def test_marking_a_feed_read_honours_the_before_cutoff(
    client: httpx.AsyncClient, api_key: str
) -> None:
    seeded = await seed(count=4)
    cutoff = 1790856000 + 86400 * 2

    await _call(client, api_key, f"api&mark=feed&as=read&id={seeded.filed_feed}&before={cutoff}")

    body = await _call(client, api_key, "api&unread_item_ids")
    unread = str(body["unread_item_ids"]).split(",")
    assert str(seeded.articles[0]) not in unread
    assert str(seeded.articles[2]) not in unread
    assert str(seeded.articles[1]) in unread
    assert str(seeded.articles[3]) in unread


async def test_marking_a_group_read_touches_only_its_feeds(
    client: httpx.AsyncClient, api_key: str
) -> None:
    seeded = await seed()

    await _call(client, api_key, f"api&mark=group&as=read&id={seeded.folder}")

    body = await _call(client, api_key, "api&unread_item_ids")
    assert body["unread_item_ids"] == str(seeded.articles[1])


async def test_marking_the_unfiled_group_read_touches_only_loose_feeds(
    client: httpx.AsyncClient, api_key: str
) -> None:
    seeded = await seed()
    groups = await _call(client, api_key, "api&groups")
    unfiled = next(
        group["id"]
        for group in groups["groups"]  # type: ignore[attr-defined]
        if group["title"] == "Unfiled"
    )

    await _call(client, api_key, f"api&mark=group&as=read&id={unfiled}")

    body = await _call(client, api_key, "api&unread_item_ids")
    assert body["unread_item_ids"] == f"{seeded.articles[0]},{seeded.articles[2]}"


async def test_group_zero_marks_everything_read(client: httpx.AsyncClient, api_key: str) -> None:
    await seed()

    await _call(client, api_key, "api&mark=group&as=read&id=0")

    assert (await _call(client, api_key, "api&unread_item_ids"))["unread_item_ids"] == ""


async def test_a_feed_cannot_be_marked_unread_in_bulk(
    client: httpx.AsyncClient, api_key: str
) -> None:
    seeded = await seed()
    await _call(client, api_key, "api&mark=group&as=read&id=0")

    await _call(client, api_key, f"api&mark=feed&as=unread&id={seeded.filed_feed}")

    assert (await _call(client, api_key, "api&unread_item_ids"))["unread_item_ids"] == ""


async def test_a_malformed_mark_changes_nothing(client: httpx.AsyncClient, api_key: str) -> None:
    await seed()

    body = await _call(client, api_key, "api&mark=banana&as=read&id=1")

    assert body["auth"] == 1
    assert (await _call(client, api_key, "api&unread_item_ids"))["unread_item_ids"] != ""


async def test_another_readers_articles_stay_out_of_reach(
    client: httpx.AsyncClient, api_key: str
) -> None:
    mine = await seed()
    second_headers = await add_second_reader()
    theirs = await seed("second@example.com")

    items = await _call(
        client, api_key, "api&items&with_ids=" + ",".join(map(str, theirs.articles))
    )
    await _call(client, api_key, f"api&mark=item&as=read&id={theirs.articles[0]}")
    await _call(client, api_key, f"api&mark=feed&as=read&id={theirs.filed_feed}")
    listed = await _call(client, api_key, "api&items&feeds&groups")

    assert items["items"] == []
    assert {item["id"] for item in listed["items"]} == set(mine.articles)  # type: ignore[attr-defined]
    assert {feed["id"] for feed in listed["feeds"]} == {mine.filed_feed, mine.loose_feed}  # type: ignore[attr-defined]
    second_key = await issue_api_key(client, second_headers)
    assert (await _call(client, second_key, "api&unread_item_ids"))["unread_item_ids"] == ",".join(
        map(str, theirs.articles)
    )
