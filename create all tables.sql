DROP TABLE IF EXISTS customer CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS pay CASCADE;
DROP TABLE IF EXISTS employee CASCADE;
DROP TABLE IF EXISTS process CASCADE;
DROP TABLE IF EXISTS department CASCADE;
DROP TABLE IF EXISTS workplace CASCADE;
DROP TABLE IF EXISTS works CASCADE;
DROP TABLE IF EXISTS office CASCADE;
DROP TABLE IF EXISTS warehouse CASCADE;
DROP TABLE IF EXISTS product CASCADE;
DROP TABLE IF EXISTS contains CASCADE;
DROP TABLE IF EXISTS supplier CASCADE;
DROP TABLE IF EXISTS delivery CASCADE;

CREATE TABLE customer(
    cust_no INTEGER PRIMARY KEY,
    name VARCHAR(80) NOT NULL,
    email VARCHAR(254) UNIQUE NOT NULL,
    phone VARCHAR(15),
    address VARCHAR(255)
);

CREATE TABLE orders(
    order_no INTEGER PRIMARY KEY,
    cust_no INTEGER NOT NULL REFERENCES customer,
    date DATE NOT NULL
    --order_no must exist in contains
);

CREATE TABLE pay(
    order_no INTEGER PRIMARY KEY REFERENCES orders,
    cust_no INTEGER NOT NULL REFERENCES customer
);

CREATE TABLE employee(
    ssn VARCHAR(20) PRIMARY KEY,
    TIN VARCHAR(20) UNIQUE NOT NULL,
    bdate DATE,
    name VARCHAR NOT NULL
    --age must be >=18
);

CREATE TABLE process(
    ssn VARCHAR(20) REFERENCES employee,
    order_no INTEGER REFERENCES orders,
    PRIMARY KEY (ssn, order_no)
);

CREATE TABLE department(
    name VARCHAR PRIMARY KEY
);

CREATE TABLE workplace(
    address VARCHAR PRIMARY KEY,
    lat NUMERIC(8, 6) NOT NULL,
    long NUMERIC(9, 6) NOT NULL,
    UNIQUE(lat, long)
    --address must be in warehouse or office but not both
);

CREATE TABLE office(
    address VARCHAR(255) PRIMARY KEY REFERENCES workplace ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE warehouse(
    address VARCHAR(255) PRIMARY KEY REFERENCES workplace ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE works(
    ssn VARCHAR(20) REFERENCES employee,
    name VARCHAR(200) REFERENCES department,
    address VARCHAR(255) REFERENCES workplace,
    PRIMARY KEY (ssn, name, address)
);

CREATE TABLE product(
    SKU VARCHAR(25) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description VARCHAR,
    price NUMERIC(10, 2) NOT NULL,
    ean NUMERIC(13) UNIQUE
);

CREATE TABLE contains(
    order_no INTEGER REFERENCES orders,
    SKU VARCHAR(25) REFERENCES product,
    qty INTEGER,
    PRIMARY KEY (order_no, SKU)
);

CREATE TABLE supplier(
    TIN VARCHAR(20) PRIMARY KEY,
    name VARCHAR(200),
    address VARCHAR(255),
    SKU VARCHAR(25) REFERENCES product,
    date DATE
);

CREATE TABLE delivery(
    address VARCHAR(255) REFERENCES warehouse,
    TIN VARCHAR(20) REFERENCES supplier,
    PRIMARY KEY (address, TIN)
);

ALTER TABLE employee
    ADD CONSTRAINT check_age CHECK (bdate <= DATE(CURRENT_DATE - interval '18 years'));
DROP TRIGGER IF EXISTS verifica_workplace ON workplace;

CREATE OR REPLACE FUNCTION verifica_workplace_trigger() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.address IN (SELECT address FROM office) AND NEW.address IN (SELECT address FROM warehouse) THEN
       RAISE EXCEPTION 'Um Workplace não pode ser Office e Warehouse ao mesmo tempo.';
    ELSIF NEW.address NOT IN (SELECT address FROM office) AND NEW.address NOT IN (SELECT address FROM warehouse) THEN
        RAISE EXCEPTION 'O Workplace % tem de ser obrigatoriamente Office ou Warehouse.', NEW.address;
    END IF;
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE CONSTRAINT TRIGGER verifica_workplace AFTER INSERT OR UPDATE ON workplace
    FOR EACH ROW EXECUTE FUNCTION verifica_workplace_trigger();

--remove foreign key constraints
ALTER TABLE office
    DROP CONSTRAINT office_address_fkey;

ALTER TABLE warehouse
    DROP CONSTRAINT warehouse_address_fkey;

--add foreign key constraints with DEFERRABLE INITIALLY DEFERRED to insert office/warehouse before workplace
--but office/warehouse and workplace need to be inserted in the same transaction
ALTER TABLE office
    ADD FOREIGN KEY (address) REFERENCES workplace
        DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE warehouse
    ADD FOREIGN KEY (address) REFERENCES workplace
        DEFERRABLE INITIALLY DEFERRED;

DROP TRIGGER IF EXISTS verifica_order ON orders;

CREATE OR REPLACE FUNCTION verifica_order_trigger() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.order_no NOT IN (SELECT order_no FROM contains) THEN
       RAISE EXCEPTION 'O order_no % tem de estar obrigatoriamente Contains.', NEW.order_no;
    END IF;
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE CONSTRAINT TRIGGER verifica_order AFTER INSERT OR UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION verifica_order_trigger();

--remove foreign key constraints
ALTER TABLE contains
    DROP CONSTRAINT contains_order_no_fkey;

--add foreign key constraints with DEFERRABLE INITIALLY DEFERRED to insert contains before orders
ALTER TABLE contains
    ADD FOREIGN KEY (order_no) REFERENCES orders
        DEFERRABLE INITIALLY DEFERRED;

START TRANSACTION;
INSERT INTO customer
VALUES (796133, 'Teresa Messias', 'teresamessias@gmail.com', '+351253243632', 'Rua Viscondessa Andaluz 101, 2005-438 Santarém'),
    (683768, 'João Moura', 'luisa47@hotmail.com', '+351956888050', 'Rua Portas Água 39, 2495-555 Fátima'),
    (425890, 'Sara Sousa', 'diana09@outlook.com', '+351956888051', 'R Nogueiras 114, 4630-167 Lameirinho'),
    (711969, 'Júlia Santos', 'jsantos@gmail.com', '+351991642731', 'Avenida José Costa Mealha 63, 8200-060 Albufeira'),
    (986101, 'Artur Machado', 'machado.yara@hotmail.com', '+351935224842', 'Rua José Fernandes Guerreiro 56, 8125-564 Quarteira'),
    (207023, 'Pablo Carbajal', 'juan198@gmail.com', '+34941646452', 'Avenida Duque Ávila 40, 2530-833 Vimeiro');

INSERT INTO product
VALUES ('2601QSVF', 'Carregador USB C', 'Carregador USB C de 100 W compacto rápido de 3 portas', 69.99, 8270248593686),
    ('009II4B7', 'Capa iPhone 14', 'Capa 5 em 1 projetada para iPhone 14 Pro, não amarela, preto fosco', 22.99, 1243711924285),
    ('G921G6KR', 'Echo Dot', 'Echo Dot (5th Gen, 2022 release)', 49.99, 9043215346764),
    ('V96KQPS8', 'Samsung Galaxy S20', 'Samsung Galaxy S20 FE 5G, 128GB, Cloud Navy', 349.99, 5314060558595),
    ('ST56K2NL', 'Apple iPhone 13', 'Apple iPhone 13, 128 GB, desbloqueado (renovado)', 606.71, 6388583724041),
    ('66M7R37H', 'Fita dupla face', 'Fita de cetim de poliéster dupla face de 2,5 cm branca, carretel de 23 metros', 7.99, 5465298380984),
    ('EY93DY43', 'Pacote 36 pilhas', 'Pacote com 36 pilhas alcalinas AAA de alto desempenho', 13.79, 8179291090863),
    ('PX74CL3V', 'Nike mens Sneaker', 'Nike Air Jordan 1 Mid masculino', 143.00, 3416777939722);

INSERT INTO contains
VALUES (64173550, '2601QSVF', 7),
    (64173550, 'PX74CL3V', 2),
    (12345633, 'G921G6KR', 12),
    (13328758, 'G921G6KR', 27),
    (86067794, '66M7R37H', 9),
    (67699100, 'ST56K2NL', 3),
    (23467187, '009II4B7', 2),
    (84534634, 'EY93DY43', 22),
    (39917206, '009II4B7', 7),
    (60520569, '2601QSVF', 8),
    (60520569, 'V96KQPS8', 1),
    (87654328, 'V96KQPS8', 2),
    (10214365, 'G921G6KR', 10);

INSERT INTO orders
VALUES (64173550, 796133, '2022-06-05'),
    (12345633, 796133, '2022-06-05'),
    (13328758, 796133, '2023-01-03'),
    (86067794, 986101, '2016-05-21'),
    (67699100, 207023, '2022-07-08'),
    (23467187, 207023, '2022-07-08'),
    (84534634, 683768, '2023-04-22'),
    (39917206, 425890, '2018-06-29'),
    (60520569, 986101, '2022-11-20'),
    (87654328, 986101, '2022-11-20'),
    (10214365, 796133, '2023-02-17');

INSERT INTO pay
VALUES (64173550, 796133),
    (13328758, 796133),
    (86067794, 986101),
    (84534634, 683768),
    (60520569, 986101);

INSERT INTO employee
VALUES ('72242192699', '888927874', '1995-06-01', 'Rafael Silva'),
    ('22744545447', '101552544', '2000-01-03', 'Jorge Pacheco'),
    ('79164512411', '737152555', '2001-02-25', 'Catarina Barbosa'),
    ('91981741707', '126395572', '1988-04-09', 'Renato Nascimento'),
    ('25442096127', '305702490', '1972-09-17', 'Raquel Almeida'),
    ('85590256266', '373193152', '1983-11-06', 'Márcio Gonçalves');

INSERT INTO process
VALUES ('72242192699', 64173550),
    ('91981741707', 84534634),
    ('25442096127', 39917206),
    ('85590256266', 86067794),
    ('85590256266', 13328758),
    ('72242192699', 60520569),
    ('85590256266', 87654328),
    ('85590256266', 23467187),
    ('85590256266', 12345633),
    ('72242192699', 67699100);

INSERT INTO department
VALUES ('Marketing'),
    ('Operacional'),
    ('Administrativo'),
    ('Financeiro'),
    ('Tecnologias da Informação'),
    ('Comercial'),
    ('Pesquisa e desenvolvimento'),
    ('Recursos Humanos');

INSERT INTO office
VALUES ('Avenida Paris 39, 2565-715 Penedo'),
    ('Rua Nossa Senhora Graça 66, 4625-012 Ariz'),
    ('Rua Sousa Lopes 34, 1349-009 Lisboa'),
    ('Rua Combatentes G Guerra 56, 3080-584 Figueira Da Foz');

INSERT INTO warehouse
VALUES ('Rua Tapada Marinha 102, 4450-594 Matosinhos'),
    ('Rua Damião Góis 35, 2685-214 Portela'),
    ('Rua Sousa Lopes 8, 1300-542 Lisboa'),
    ('Rua Tapada Marinha 53, 4450-365 Matosinhos');

INSERT INTO workplace
VALUES ('Avenida Paris 39, 2565-715 Penedo', 39.066590, -9.202043),
    ('Rua Tapada Marinha 102, 4450-594 Matosinhos', 41.197019, -8.701277),
    ('Rua Nossa Senhora Graça 66, 4625-012 Ariz', 41.120380, -8.186483),
    ('Rua Damião Góis 35, 2685-214 Portela', 38.780147, -9.110526),
    ('Rua Sousa Lopes 8, 1300-542 Lisboa', 38.703954, -9.193210),
    ('Rua Combatentes G Guerra 56, 3080-584 Figueira Da Foz', 40.159144, -8.859109),
    ('Rua Sousa Lopes 34, 1349-009 Lisboa', 38.703953, -9.193211),
    ('Rua Tapada Marinha 53, 4450-365 Matosinhos', 41.191684, -8.677048);

INSERT INTO works
VALUES ('72242192699', 'Marketing', 'Rua Sousa Lopes 34, 1349-009 Lisboa'),
    ('22744545447', 'Administrativo', 'Rua Tapada Marinha 102, 4450-594 Matosinhos'),
    ('91981741707', 'Operacional', 'Rua Sousa Lopes 8, 1300-542 Lisboa'),
    ('79164512411', 'Tecnologias da Informação', 'Rua Damião Góis 35, 2685-214 Portela'),
    ('25442096127', 'Financeiro', 'Rua Tapada Marinha 102, 4450-594 Matosinhos'),
    ('85590256266', 'Operacional', 'Rua Tapada Marinha 53, 4450-365 Matosinhos');

INSERT INTO supplier
VALUES ('875990353', 'Anker', 'Rua Projectada 119, 2900-336 Setúbal', '2601QSVF', '2015-02-15'),
     ('427520362', 'Tauri', 'Rua Florbela Espanca 113, 2845-545 Amora', '009II4B7', '2016-01-16'),
     ('812007893', 'Vatin', 'Rua Forças Armadas 67, 7670-132 Garvão', '66M7R37H', '2022-08-10'),
     ('397096211', 'Amazon Basics', 'Rua Oliveirinhas 79, 4420-609 Gondomar', 'EY93DY43', '2023-02-01'),
     ('481735845', 'Daytu Sangyo', 'Rua Nogueiras 103, 4630-394 Marco De Canaveses', 'PX74CL3V', '2023-04-13');

INSERT INTO delivery
VALUES ('Rua Sousa Lopes 8, 1300-542 Lisboa', '875990353'),
    ('Rua Sousa Lopes 8, 1300-542 Lisboa', '812007893'),
    ('Rua Damião Góis 35, 2685-214 Portela', '397096211'),
    ('Rua Damião Góis 35, 2685-214 Portela', '427520362'),
    ('Rua Tapada Marinha 102, 4450-594 Matosinhos', '397096211'),
    ('Rua Tapada Marinha 53, 4450-365 Matosinhos', '481735845');
COMMIT;
