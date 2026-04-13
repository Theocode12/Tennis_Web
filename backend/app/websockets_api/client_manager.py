import configparser

import socketio  # type: ignore


def client_manager_factory(
    config: configparser.ConfigParser,
) -> socketio.AsyncManager:
    client_manager = config.get("app", "socketClientManger", fallback="manager")
    if client_manager == "redis":
        from socketio import AsyncRedisManager

        url = config.get("app", "redisUrl")
        return AsyncRedisManager(url)
    else:
        from socketio import AsyncManager

        return AsyncManager()
