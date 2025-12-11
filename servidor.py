#!/usr/bin/env python3
import os
import subprocess
import sys
from textwrap import dedent

BANNER = r"""
███████╗███████╗██████╗ ██╗   ██╗██╗██████╗  ██████╗ ███████╗
██╔════╝██╔════╝██╔══██╗██║   ██║██║██╔══██╗██╔════╝ ██╔════╝
███████╗█████╗  ██████╔╝██║   ██║██║██████╔╝██║  ███╗█████╗  
╚════██║██╔══╝  ██╔══██╗██║   ██║██║██╔══██╗██║   ██║██╔══╝  
███████║███████╗██║  ██║╚██████╔╝██║██║  ██║╚██████╔╝███████╗
╚══════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝

              powered by GRENDES1
"""

def run(cmd: str):
    print(f"\n[+] Ejecutando: {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def check_root():
    if os.geteuid() != 0:
        print("Este script debe ejecutarse como root (sudo).", file=sys.stderr)
        sys.exit(1)

def base_update():
    run("apt update -y")
    run("apt upgrade -y")

def install_lamp_base():
    print("\n--- Instalando pila LAMP básica (Apache, MySQL/MariaDB, PHP) ---")
    base_update()
    run(
        "apt install -y apache2 mysql-server php libapache2-mod-php "
        "php-mysql php-xml php-gd php-curl php-zip php-mbstring php-intl "
        "wget unzip"
    )
    run("systemctl enable --now apache2")
    run("systemctl enable --now mysql")
    print("\n[OK] Pila LAMP instalada.")

def create_mysql_db_and_user(db_name, db_user, db_password):
    sql = f"""\
CREATE DATABASE {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
CREATE USER '{db_user}'@'localhost' IDENTIFIED BY '{db_password}';
GRANT ALL PRIVILEGES ON {db_name}.* TO '{db_user}'@'localhost';
FLUSH PRIVILEGES;
"""
    print("\n[+] Creando base de datos y usuario MySQL...")
    print("(Nota: evita caracteres raros como comillas o símbolos muy extraños en la contraseña.)")
    run(f"mysql <<'EOF'\n{sql}\nEOF")

def configure_apache_vhost(domain, docroot):
    conf_path = f"/etc/apache2/sites-available/{domain}.conf"
    print(f"\n[+] Creando VirtualHost de Apache: {conf_path}")
    vhost = dedent(f"""\
    <VirtualHost *:80>
        ServerName {domain}
        ServerAdmin webmaster@{domain}
        DocumentRoot {docroot}

        <Directory {docroot}>
            AllowOverride All
            Require all granted
        </Directory>

        ErrorLog ${{APACHE_LOG_DIR}}/{domain}_error.log
        CustomLog ${{APACHE_LOG_DIR}}/{domain}_access.log combined
    </VirtualHost>
    """)
    with open(conf_path, "w") as f:
        f.write(vhost)

    run("a2enmod rewrite")
    run(f"a2ensite {domain}.conf")
    run("a2dissite 000-default.conf || true")
    run("systemctl reload apache2")

def install_wordpress():
    print("\n=== Instalación de WordPress (gestor de contenidos) ===")
    domain = input("Dominio que quieres usar (ej: midominio.com): ").strip()
    db_name = input("Nombre de la base de datos para WordPress (ej: wp_db): ").strip()
    db_user = input("Usuario MySQL para WordPress (ej: wp_user): ").strip()
    db_password = input("Contraseña para ese usuario MySQL: ").strip()

    install_lamp_base()
    create_mysql_db_and_user(db_name, db_user, db_password)

    web_root = f"/var/www/{domain}"
    run("mkdir -p /var/www")
    run(f"rm -rf {web_root}")
    run("cd /tmp && rm -f latest.tar.gz && wget https://wordpress.org/latest.tar.gz")
    run("cd /tmp && tar xzf latest.tar.gz")
    run(f"mv /tmp/wordpress {web_root}")
    run(f"chown -R www-data:www-data {web_root}")
    run(f"chmod -R 755 {web_root}")

    wp_config = os.path.join(web_root, "wp-config.php")
    run(f"cp {web_root}/wp-config-sample.php {wp_config}")
    run(f"sed -i 's/database_name_here/{db_name}/' {wp_config}")
    run(f"sed -i 's/username_here/{db_user}/' {wp_config}")
    run(f"sed -i 's/password_here/{db_password}/' {wp_config}")

    configure_apache_vhost(domain, web_root)
    print("\n[OK] WordPress instalado.")
    print(f"Abre http://{domain} en tu navegador para terminar la instalación web.")

def install_nextcloud():
    print("\n=== Instalación de Nextcloud (servidor de archivos) ===")
    domain = input("Dominio que quieres usar para Nextcloud (ej: cloud.midominio.com): ").strip()
    db_name = input("Nombre de la base de datos para Nextcloud (ej: nextcloud_db): ").strip()
    db_user = input("Usuario MySQL para Nextcloud (ej: nextcloud_user): ").strip()
    db_password = input("Contraseña para ese usuario MySQL: ").strip()

    install_lamp_base()
    # Paquetes PHP extra recomendados para Nextcloud
    run("apt install -y php-imagick php-bcmath")
    create_mysql_db_and_user(db_name, db_user, db_password)

    web_root = f"/var/www/{domain}"
    data_dir = f"/var/www/{domain}_data"

    run("cd /tmp && rm -f nextcloud-*.zip && wget https://download.nextcloud.com/server/releases/latest.zip -O nextcloud_latest.zip")
    run("cd /tmp && unzip -o nextcloud_latest.zip")
    run("mkdir -p /var/www")
    run(f"rm -rf {web_root}")
    run(f"mv /tmp/nextcloud {web_root}")
    run(f"mkdir -p {data_dir}")
    run(f"chown -R www-data:www-data {web_root} {data_dir}")
    run(f"chmod -R 750 {web_root} {data_dir}")

    configure_apache_vhost(domain, web_root)

    print("\n[OK] Nextcloud instalado.")
    print(f"Abre http://{domain} en tu navegador.")
    print("En el formulario de instalación de Nextcloud usa los datos de la base de datos que acabas de definir.")

def main():
    check_root()
    print(BANNER)
    print("Este script está pensado para Ubuntu Server 22.04 LTS.")
    while True:
        print("""\
¿Qué quieres hacer?

  [1] Crear un gestor de contenido (WordPress)
  [2] Crear un servidor de archivos (Nextcloud)
  [3] Instalar solo la pila LAMP básica
  [0] Salir
""")
        opcion = input("Elige una opción: ").strip()
        if opcion == "1":
            install_wordpress()
        elif opcion == "2":
            install_nextcloud()
        elif opcion == "3":
            install_lamp_base()
        elif opcion == "0":
            print("Saliendo...")
            break
        else:
            print("Opción no válida. Intenta de nuevo.")

if __name__ == "__main__":
    main()
