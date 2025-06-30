CREATE TABLE IF NOT EXISTS pages (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    url TEXT,
    url_hash CHAR(64) NOT NULL UNIQUE,
    title TEXT,
    summary TEXT,
    labels TEXT,
    keywords TEXT,
    search_query TEXT,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS page_visits (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    page_id BIGINT UNSIGNED NOT NULL,
    user_id VARCHAR(255),
    session_id VARCHAR(255),
    scroll_depth FLOAT,
    visit_start DATETIME,
    visit_end DATETIME,
    PRIMARY KEY (id),
    FOREIGN KEY (page_id) REFERENCES pages(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS root_categories (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(255) UNIQUE,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS sub_categories (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    root_id BIGINT UNSIGNED NOT NULL,
    name VARCHAR(255),
    PRIMARY KEY (id),
    FOREIGN KEY (root_id) REFERENCES root_categories(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS page_categories (
    page_id BIGINT UNSIGNED NOT NULL,
    sub_id BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (page_id, sub_id),
    FOREIGN KEY (page_id) REFERENCES pages(id),
    FOREIGN KEY (sub_id) REFERENCES sub_categories(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
