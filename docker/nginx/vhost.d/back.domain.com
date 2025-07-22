location /static/ {
    alias /app/static/;
    expires 1y;
    add_header Cache-Control "public, immutable";
    access_log off;
}

# Serve Django media files
location /media/ {
    alias /app/media/;
    expires 30d;
    add_header Cache-Control "public";
}

# Health check
location /health {
    access_log off;
    return 200 "api healthy\n";
    add_header Content-Type text/plain;
}
