dir=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
date=`date +%Y-%m-%d`
install_log="${dir}/TestDbSetUp_${date}_log.txt"
read -e -p "Password of the 'root' user of MySQL: " -i "" db_root_password
# Verify password
while ! mysql -u root --password="${db_root_password}"  -e ";" ; do
       read -e -p "Invalid password, please retry: " -i "" db_root_password
done
db_user="pipot"
db_name="pipotTest"
mysql -u root --password="${db_root_password}" -e "CREATE DATABASE IF NOT EXISTS ${db_name};" >> "$install_log" 2>&1
# Check if DB exists
db_exists=`mysql -u root --password="${db_root_password}" -se"USE ${db_name};" 2>&1`
if [ ! "${db_exists}" == "" ]; then
    echo "Failed to create the database! Please check the installation log!"
    exit -1
fi
# Check if user exists
db_user_exists=`mysql -u root --password="${db_root_password}" -sse "SELECT EXISTS(SELECT 1 FROM mysql.user WHERE user = '${db_user}')"`
db_user_password=""
if [ ${db_user_exists} = 0 ]; then
    rand_pass=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 16 | head -n 1)
    read -e -p "Password for ${db_user} (will be created): " -i "${rand_pass}" db_user_password
    # Attempt to create the user
    mysql -u root --password="$db_root_password" -e "CREATE USER '${db_user}'@'localhost' IDENTIFIED BY '${db_user_password}';" >> "$install_log" 2>&1
    db_user_exists=`mysql -u root --password="$db_root_password" -sse "SELECT EXISTS(SELECT 1 FROM mysql.user WHERE user = '$db_user')"`
    if [ ${db_user_exists} = 0 ]; then
        echo "Failed to create the user! Please check the installation log!"
        exit -1
    fi
else
    read -e -p "Password for ${db_user}: " db_user_password
    # Check if we have access
    while ! mysql -u "${db_user}" --password="${db_user_password}"  -e ";" ; do
       read -e -p "Invalid password, please retry: " -i "" db_user_password
    done
fi
# Grant user access to database
mysql -u root --password="${db_root_password}" -e "GRANT ALL ON ${db_name}.* TO '${db_user}'@'localhost';" >> "$install_log" 2>&1
# Check if user has access
db_access=`mysql -u "${db_user}" --password="${db_user_password}" -se"USE ${db_name};" 2>&1`
if [ ! "${db_access}" == "" ]; then
    echo "Failed to grant user access to database! Please check the installation log!"
    exit -1
fi

echo "# Auto-generated configuration by installTestDb.sh
DATABASE_URI = 'mysql+pymysql://${db_user}:${db_user_password}@localhost:3306/${db_name}'
" > "${dir}/tests/config.py"