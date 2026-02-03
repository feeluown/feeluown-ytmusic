import json
import logging
from http.cookies import SimpleCookie
from typing import List

from ytmusicapi.constants import YTM_DOMAIN

logger = logging.getLogger(__name__)


class YtmusicProfileManager:
    """Handle profile discovery and switching for authenticated YT Music sessions."""
    def __init__(self, service):
        # Service provides session, auth headers, and API helpers.
        self._service = service
        self._account_override = None
        self._forced_gaia_id = None

    def get_current_account_info(self) -> dict:
        """Return the active profile info, using switcher/accounts_list as sources."""
        self._service.api._check_auth()
        if self._account_override is not None:
            return self._account_override

        # Prefer the account switcher endpoint when available.
        switcher = self._get_account_switcher()
        if switcher is not None:
            items = self._find_account_items(switcher)
            datasync_id = self._extract_datasync_id(switcher)
            selected = self._pick_account_item(
                items, datasync_id, self._forced_gaia_id
            )
            if selected is not None:
                info = self._build_account_info(selected)
                if info is not None:
                    if not info.get("channelId"):
                        channel_id = self._extract_channel_id_from_menu()
                        if channel_id:
                            info["channelId"] = channel_id
                    return info

        # Fall back to accounts_list when switcher is unavailable.
        raise ValueError(
            "No account info available; cookies or authorization may be expired."
        )

    def list_profiles(self) -> List[dict]:
        """List selectable profiles (filtering out items without channel handles)."""
        switcher = self._get_account_switcher()
        if switcher is None:
            return []

        items = self._find_account_items(switcher)
        datasync_id = self._extract_datasync_id(switcher)
        profiles = []
        for item in items:
            name = self._extract_text(item.get("accountName"))
            if not name:
                continue
            channel_handle = self._extract_text(item.get("channelHandle"))
            if not channel_handle:
                continue
            profiles.append(
                {
                    "accountName": name,
                    "channelHandle": channel_handle,
                    "accountPhotoUrl": self._extract_thumbnail_url(
                        item.get("accountPhoto")
                    ),
                    "channelId": self._extract_channel_id(item),
                    "gaiaId": self._extract_obfuscated_gaia_id(item),
                    "isSelected": self._is_item_selected(item, datasync_id),
                }
            )
        return profiles

    def switch_profile(self, account_name: str = None, gaia_id: str = None) -> dict:
        """Switch current profile by name or gaia_id; returns new profile info."""
        if not account_name and not gaia_id:
            self._set_on_behalf_of_user(None)
            self._account_override = None
            self._forced_gaia_id = None
            return self.get_current_account_info()

        switcher = self._get_account_switcher()
        if switcher is None:
            raise ValueError("No account switcher data available")

        items = self._find_account_items(switcher)
        selected = None
        if gaia_id:
            for item in items:
                if self._extract_obfuscated_gaia_id(item) == gaia_id:
                    selected = item
                    break
        else:
            selected = self._find_account_item_by_name(items, account_name)

        if selected is None:
            raise ValueError("Profile not found")

        selected_gaia_id = self._extract_obfuscated_gaia_id(selected)
        self._set_on_behalf_of_user(selected_gaia_id)
        self._forced_gaia_id = selected_gaia_id
        self._account_override = self._build_account_info(selected)
        if self._account_override and not self._account_override.get("channelId"):
            channel_id = self._extract_channel_id_from_menu()
            if channel_id:
                self._account_override["channelId"] = channel_id
        return self._account_override

    def _set_on_behalf_of_user(self, gaia_id):
        # YTMusic uses onBehalfOfUser to scope requests to a specific profile.
        context = self._service.api.context.setdefault("context", {})
        user_ctx = context.setdefault("user", {})
        if gaia_id:
            user_ctx["onBehalfOfUser"] = gaia_id
        else:
            user_ctx.pop("onBehalfOfUser", None)

    def _get_account_switcher(self):
        # Account switcher returns the richest profile list, including selection state.
        response = self._request_account_switcher(
            url="https://music.youtube.com/getAccountSwitcherEndpoint",
            origin=YTM_DOMAIN,
        )
        if self._has_account_items(response):
            return response
        return None

    def _request_account_switcher(self, url, origin):
        try:
            headers = dict(self._service.api.headers)
            headers["origin"] = origin
            response = self._service._session.request(
                "GET",
                url,
                headers=headers,
                proxies=self._service._session.proxies,
                cookies=self._service.api.cookies,
            )
            response_text = response.text
        except Exception as e:
            logger.debug("account switcher request failed: %s", e)
            return None

        if response.status_code >= 400:
            logger.debug(
                "account switcher request failed with status %s",
                response.status_code,
            )
            return None

        # Some responses update auth cookies; keep them in sync.
        self._update_auth_cookie_from_response(response)

        payload = self._strip_xssi_prefix(response_text)
        try:
            return json.loads(payload)
        except Exception as e:
            logger.debug("account switcher parse failed: %s", e)
            return None

    @classmethod
    def _strip_xssi_prefix(cls, text):
        if not isinstance(text, str):
            return text
        if text.startswith(")]}'"):
            newline = text.find("\n")
            if newline != -1:
                return text[newline + 1 :]
            return text[4:]
        return text

    def _extract_channel_id_from_menu(self):
        # account_menu does not always include it, but can expose a channel browseId.
        try:
            response = self._service.api._send_request("account/account_menu", {})
        except Exception as e:
            logger.debug("account_menu request failed: %s", e)
            return None
        return self._find_channel_browse_id(response)

    @classmethod
    def _find_account_items(cls, data):
        items = []
        if isinstance(data, dict):
            for key in ("accountItem", "accountItemRenderer"):
                item = data.get(key)
                if isinstance(item, dict):
                    items.append(item)
            for value in data.values():
                items.extend(cls._find_account_items(value))
        elif isinstance(data, list):
            for value in data:
                items.extend(cls._find_account_items(value))
        return items

    @classmethod
    def _find_channel_browse_id(cls, data):
        # Look for a user channel browseId in any nested browseEndpoint.
        if isinstance(data, dict):
            browse_endpoint = data.get("browseEndpoint")
            if isinstance(browse_endpoint, dict):
                browse_id = browse_endpoint.get("browseId")
                if browse_id and str(browse_id).startswith("UC"):
                    return browse_id
                page_type = (
                    browse_endpoint.get("browseEndpointContextSupportedConfigs", {})
                    .get("browseEndpointContextMusicConfig", {})
                    .get("pageType")
                )
                if page_type == "MUSIC_PAGE_TYPE_USER_CHANNEL" and browse_id:
                    return browse_id
            for value in data.values():
                found = cls._find_channel_browse_id(value)
                if found:
                    return found
        elif isinstance(data, list):
            for value in data:
                found = cls._find_channel_browse_id(value)
                if found:
                    return found
        return None

    @classmethod
    def _pick_account_item(cls, items, datasync_id=None, gaia_id=None):
        # Explicit gaia_id wins; otherwise rely on selection flags or datasync_id.
        if gaia_id:
            for item in items:
                if cls._extract_obfuscated_gaia_id(item) == gaia_id:
                    return item
        for item in items:
            if item.get("isSelected") or item.get("isCurrent") or item.get("isActive"):
                return item
        if datasync_id:
            for item in items:
                if cls._extract_obfuscated_gaia_id(item) == datasync_id:
                    return item
        return None

    @classmethod
    def _find_account_item_by_name(cls, items, name):
        if not name:
            return None
        for item in items:
            if cls._extract_text(item.get("accountName")) == name:
                return item
        return None

    @classmethod
    def _extract_datasync_id(cls, response):
        if not isinstance(response, dict):
            return None
        response_context = response.get("responseContext", {})
        main_context = response_context.get("mainAppWebResponseContext", {})
        datasync_id = main_context.get("datasyncId")
        if not datasync_id or not isinstance(datasync_id, str):
            return None
        return datasync_id.split("||", 1)[0]

    @classmethod
    def _extract_obfuscated_gaia_id(cls, item):
        if not isinstance(item, dict):
            return None
        service_endpoint = item.get("serviceEndpoint", {})
        select_endpoint = service_endpoint.get("selectActiveIdentityEndpoint", {})
        tokens = select_endpoint.get("supportedTokens", [])
        if not isinstance(tokens, list):
            return None
        for token in tokens:
            account_state = token.get("accountStateToken")
            if isinstance(account_state, dict):
                obfuscated_id = account_state.get("obfuscatedGaiaId")
                if obfuscated_id:
                    return obfuscated_id
        return None

    @classmethod
    def _has_account_items(cls, response):
        if response is None:
            return False
        return bool(cls._find_account_items(response))

    def _update_auth_cookie_from_response(self, response):
        # Merge Set-Cookie from the response into the current auth cookie header.
        try:
            cookie_header = self._service.api.headers.get("cookie", "")
        except Exception:
            cookie_header = ""
        if not response.cookies:
            return
        jar = SimpleCookie()
        if cookie_header:
            jar.load(cookie_header)
        for cookie in response.cookies:
            jar[cookie.name] = cookie.value
        new_cookie = "; ".join([f"{m.key}={m.value}" for m in jar.values()])
        if new_cookie:
            self._service.api._auth_headers["cookie"] = new_cookie

    @classmethod
    def _extract_text(cls, value):
        if isinstance(value, dict):
            runs = value.get("runs")
            if isinstance(runs, list) and runs:
                text = runs[0].get("text")
                if text:
                    return text
            simple_text = value.get("simpleText")
            if simple_text:
                return simple_text
        if isinstance(value, str):
            return value
        return None

    @classmethod
    def _build_account_info(cls, item):
        account_name = cls._extract_text(item.get("accountName"))
        if not account_name:
            return None
        channel_handle = cls._extract_text(item.get("channelHandle"))
        channel_id = cls._extract_channel_id(item)
        account_photo_url = cls._extract_thumbnail_url(
            item.get("accountPhoto")
        )
        return {
            "accountName": account_name,
            "channelHandle": channel_handle,
            "accountPhotoUrl": account_photo_url,
            "channelId": channel_id,
        }

    @classmethod
    def _extract_thumbnail_url(cls, account_photo):
        if not isinstance(account_photo, dict):
            return None
        thumbnails = account_photo.get("thumbnails")
        if isinstance(thumbnails, list) and thumbnails:
            return thumbnails[0].get("url")
        return None

    @classmethod
    def _extract_channel_id(cls, item):
        if not isinstance(item, dict):
            return None
        return item.get("channelId")

    @classmethod
    def _is_item_selected(cls, item, datasync_id=None):
        if item.get("isSelected") or item.get("isCurrent") or item.get("isActive"):
            return True
        if datasync_id:
            return cls._extract_obfuscated_gaia_id(item) == datasync_id
        return False
