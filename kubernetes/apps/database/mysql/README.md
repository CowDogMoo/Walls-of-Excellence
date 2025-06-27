# MySQL

MySQL is a popular open-source relational database management system (RDBMS).

## Accessing MySQL

1. **Within the cluster:**
   Use the service name `mysql.database.svc.cluster.local` on port 3306.

2. **Get the root password:**

   ```bash
   kubectl get secret mysql-secret -n database -o jsonpath='{.data.root-password}' | base64 --decode
   ```

3. **Connect to MySQL:**
   For testing purposes, you can use the following command to connect to MySQL
   directly from the command line:

   ```bash
   kubectl run -it --rm --image=mysql:8.0 --restart=Never mysql-client -- mysql -h mysql.database.svc.cluster.local -uroot -p$(kubectl get secret mysql-secret -n database -o jsonpath='{.data.root-password}' | base64 --decode)
   ```

   This command will:
   - Create a temporary pod with the MySQL client
   - Connect to the MySQL server using the correct host and credentials
   - Automatically clean up the pod after you're done

   You should see output similar to this:

   ```bash
   If you don't see a command prompt, try pressing enter.
   Welcome to the MySQL monitor.  Commands end with ; or \g.
   Your MySQL connection id is 9
   Server version: 8.0.39 MySQL Community Server - GPL

   Copyright (c) 2000, 2024, Oracle and/or its affiliates.

   Oracle is a registered trademark of Oracle Corporation and/or its
   affiliates. Other names may be trademarks of their respective
   owners.

   Type 'help;' or '\h' for help. Type '\c' to clear the current input statement.

   mysql>
   ```

   You can now run MySQL commands directly. When you're done, type `exit` to
   close the connection and remove the temporary pod.
