import time
from typing import Any

import requests


class ApiError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class ExamApi:
    def __init__(self, server_url: str, timeout: float = 10.0):
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout
        self.token: str | None = None
        self._http = requests.Session()

    def _request(self, method: str, path: str, retries: int = 2, **kwargs: Any) -> Any:
        headers = dict(kwargs.pop("headers", {}))
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                response = self._http.request(
                    method,
                    self.server_url + path,
                    timeout=self.timeout,
                    headers=headers,
                    **kwargs,
                )
            except requests.RequestException as exc:
                last_error = exc
                if attempt < retries:
                    time.sleep(1.0 * (attempt + 1))
                    continue
                raise ApiError("сервер недоступен, проверьте подключение") from exc
            if response.status_code == 401:
                raise ApiError("сессия истекла. войдите заново.", 401)
            if response.status_code >= 400:
                try:
                    detail = response.json().get("detail", response.text)
                except ValueError:
                    detail = response.text
                raise ApiError(str(detail), response.status_code)
            if not response.content:
                return None
            return response.json()

        raise ApiError("сервер недоступен.") from last_error

    def health(self, timeout: float = 3.0) -> dict:
        response = self._http.get(self.server_url + "/api/health", timeout=timeout)
        if response.status_code != 200:
            raise ApiError(f"сервер ответил кодом {response.status_code}", response.status_code)
        try:
            return response.json()
        except ValueError:
            raise ApiError(
                "сервер вернул не-JSON (на этом порту работает не экзаменационный сервер "
                f"или SPA перехватывает API): {response.text[:100]!r}"
            )
    
    def get_schools(self) -> list[dict]:
        return self._request("GET", "/api/public/schools")

    def get_exam_info(self) -> dict:
        return self._request("GET", "/api/public/exam-info")

    def student_login(self, payload: dict) -> dict:
        data = self._request("POST", "/api/student/login", json=payload)
        self.token = data["access_token"]
        return data["student"]

    def start_attempt(self, machine_id: str) -> dict:
        return self._request(
            "POST", "/api/student/attempts/start", json={"machine_id": machine_id}
        )

    def get_attempt(self, attempt_id: int) -> dict:
        return self._request("GET", f"/api/student/attempts/{attempt_id}")

    def save_answers(self, attempt_id: int, answers: list[dict]) -> dict:
        return self._request(
            "PUT",
            f"/api/student/attempts/{attempt_id}/answers",
            json={"answers": answers},
        )

    def send_events(self, attempt_id: int, events: list[dict]) -> dict:
        return self._request(
            "POST",
            f"/api/student/attempts/{attempt_id}/events",
            json={"events": events},
        )

    def finish(self, attempt_id: int, reason: str, answers: list[dict], retries: int = 2) -> dict:
        return self._request(
            "POST",
            f"/api/student/attempts/{attempt_id}/finish",
            json={"reason": reason, "answers": answers},
            retries=retries,
        )

    def download_file(self, file_id: int) -> bytes:
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        response = self._http.get(
            self.server_url + f"/api/files/{file_id}", headers=headers, timeout=60
        )
        if response.status_code >= 400:
            raise ApiError("не удалось скачать файл", response.status_code)
        return response.content