-- Create a dedicated database for Temporal so its schema never shares the
-- application database. Runs once on first Postgres cluster initialisation.
CREATE DATABASE temporal;
