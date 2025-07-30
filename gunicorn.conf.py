workers = 2  # Оптимально для Fly.io (1-2 workers)  
worker_class = "uvicorn.workers.UvicornWorker"  
bind = "0.0.0.0:8080"  
timeout = 120  
keepalive = 5  