CONFIG = {
    "app": {
        "redisUrl": "redis://localhost:6379",
        "enableStorage": True,
        "storageType": "redis",
        "ttl": 43200,
        "fileStorageDir": "game_data",
    },
    "logging": {
        "enabled": True,
        "level": "DEBUG",
        "consoleLogs": False,
        "serverLogs": False,
        "serverLogFile": "logs/server.log",
        "maxFileSize": 10485760,
        "backupCount": 5,
    },
}
