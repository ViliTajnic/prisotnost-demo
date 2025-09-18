#!/bin/bash

# Custom Oracle 23ai initialization script for M4 Mac
# This bypasses the problematic listener configuration

echo "Starting Oracle 23ai Free initialization..."

# Set Oracle environment
export ORACLE_HOME=/opt/oracle/product/23ai/dbhomeFree
export ORACLE_SID=FREE
export PATH=$ORACLE_HOME/bin:$PATH

# Start Oracle instance
echo "Starting Oracle database instance..."
su - oracle -c "
export ORACLE_HOME=/opt/oracle/product/23ai/dbhomeFree
export ORACLE_SID=FREE
export PATH=\$ORACLE_HOME/bin:\$PATH

# Create basic listener.ora if it doesn't exist
mkdir -p \$ORACLE_HOME/network/admin
cat > \$ORACLE_HOME/network/admin/listener.ora << 'EOF'
LISTENER =
  (DESCRIPTION_LIST =
    (DESCRIPTION =
      (ADDRESS = (PROTOCOL = TCP)(HOST = 0.0.0.0)(PORT = 1521))
    )
  )

SID_LIST_LISTENER =
  (SID_LIST =
    (SID_DESC =
      (SID_NAME = FREE)
      (ORACLE_HOME = /opt/oracle/product/23ai/dbhomeFree)
    )
  )
EOF

# Start listener manually
lsnrctl start

# Start database
sqlplus / as sysdba << 'EOSQL'
startup;
alter pluggable database FREEPDB1 open;
exit;
EOSQL
"

echo "Oracle 23ai Free is ready!"

# Keep container running
tail -f /dev/null