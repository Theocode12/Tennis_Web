CONFIG = {
    "app": {
        "redisUrl": "redis://localhost:6379",
        "enableStorage": True,
        "storageType": "redis",
        "fileStorageDir": "game_data",
    },
    "logging": {
        "enabled": True,
        "level": "DEBUG",
        "consoleLogs": False,
        "serverLogs": True,
        "serverLogFile": "logs/server.log",
        "maxFileSize": 10485760,
        "backupCount": 5,
    },
}
