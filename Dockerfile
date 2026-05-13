# design_doc §7.1 — Python 3.11-slim
# Phase 1: psycopg2-binary 自带驱动，无需任何系统包
# Phase 2: 需要添加 WeasyPrint 系统依赖时再取消下方注释
FROM python:3.11-slim

WORKDIR /app

# Phase 2 时取消注释（WeasyPrint 需要 pango/cairo）:
# RUN apt-get update && apt-get install -y \
#     libpango-1.0-0 \
#     libpangoft2-1.0-0 \
#     libpangocairo-1.0-0 \
#     libgdk-pixbuf-xlib-2.0-0 \
#     libffi-dev \
#     shared-mime-info \
#     && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Phase 5 生产环境换成 gunicorn
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
