server {
    listen 64.13.139.229:443 ssl; # managed by Certbot
    server_name  challenge.bx9.net;

    access_log  /var/log/nginx/challenge.bx9.net.log  main;
    add_header Permissions-Policy interest-cohort=() always;

    location / {
        root   /home/astrogreg/github/ngeht-analysis-content/live-website/;
        index  index.html;
    }

    location /upload {
       proxy_pass http://localhost:8001;
       proxy_http_version 1.1;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    ssl_certificate /etc/letsencrypt/live/challenge.bx9.net/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/challenge.bx9.net/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot
}

server {
    listen       64.13.139.229:80;
    server_name  challenge.bx9.net;

    access_log /var/log/nginx/lindahl_redir.log main;
    add_header Permissions-Policy interest-cohort=() always;

    location /.well-known/ {
        root   /home/astrogreg/github/ngeht-analysis-content/live-website/.well-known/;
        index  index.html;
    }

    location / {
        rewrite ^/(.*)$ https://$host/$1 redirect;
    }
}

server {
    listen 64.13.139.229:443 ssl; # managed by Certbot
    server_name  test.challenge.bx9.net;

    access_log  /var/log/nginx/challenge.bx9.net.log  main;
    add_header Permissions-Policy interest-cohort=() always;

    location / {
        root   /home/astrogreg/github/ngeht-analysis-content/test-website/;
        index  index.html;
    }

    location /upload {
       proxy_pass http://localhost:8001;
       proxy_http_version 1.1;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    ssl_certificate /etc/letsencrypt/live/test.challenge.bx9.net/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/test.challenge.bx9.net/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot
}

server {
    listen       64.13.139.229:80;
    server_name  test.challenge.bx9.net;

    access_log /var/log/nginx/lindahl_redir.log main;
    add_header Permissions-Policy interest-cohort=() always;

    location /.well-known/ {
        root   /home/astrogreg/github/ngeht-analysis-content/test-website/.well-known/;
        index  index.html;
    }

    location / {
        rewrite ^/(.*)$ https://$host/$1 redirect;
    }
}

server {
    listen 64.13.139.229:443 ssl; # managed by Certbot
    server_name  challenge.ngeht.org;

    access_log  /var/log/nginx/challenge.ngeht.org.log  main;
    add_header Permissions-Policy interest-cohort=() always;

    location / {
        root   /home/astrogreg/github/ngeht-analysis-content/live-website/;
        index  index.html;
    }

    location /upload {
       proxy_pass http://localhost:8001;
       proxy_http_version 1.1;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    ssl_certificate /etc/letsencrypt/live/challenge.ngeht.org/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/challenge.ngeht.org/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot
}

server {
    listen       64.13.139.229:80;
    server_name  challenge.ngeht.org;

    access_log /var/log/nginx/lindahl_redir.log main;
    add_header Permissions-Policy interest-cohort=() always;

    location /.well-known/ {
        root   /home/astrogreg/github/ngeht-analysis-content/live-website/.well-known/;
        index  index.html;
    }

    location / {
        rewrite ^/(.*)$ https://$host/$1 redirect;
    }
}
