DROP TABLE IF EXISTS `usuarios`;
CREATE TABLE `usuarios` (
    `id`              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `nombre`          VARCHAR(120) NOT NULL,
    `apellido`        VARCHAR(120) NOT NULL,
    `email`           VARCHAR(120) NOT NULL UNIQUE,
    `empresa`         VARCHAR(200) DEFAULT NULL,
    `telefono`        VARCHAR(20) DEFAULT NULL,
    `password`        VARCHAR(255) NOT NULL,
    `fecha_registro`  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Índice adicional para búsquedas por email (login rápido)
CREATE INDEX `idx_usuarios_email` ON `usuarios`(`email`);


-- --------------------------------------------------------
-- Tabla: mensajes_contacto
-- Almacena los mensajes enviados desde el formulario de contacto
-- --------------------------------------------------------
DROP TABLE IF EXISTS `mensajes_contacto`;
CREATE TABLE `mensajes_contacto` (
    `id`              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `nombre`          VARCHAR(120) NOT NULL,
    `email`           VARCHAR(120) NOT NULL,
    `mensaje`         TEXT NOT NULL,
    `respuesta_admin` TEXT DEFAULT NULL,
    `estado`          VARCHAR(20) DEFAULT 'nuevo' NOT NULL,
    `fecha_registro`  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Índices para filtrar mensajes
CREATE INDEX `idx_mensajes_email`   ON `mensajes_contacto`(`email`);
CREATE INDEX `idx_mensajes_estado`  ON `mensajes_contacto`(`estado`);


-- ============================================================
-- DATOS DE EJEMPLO (opcional, eliminar si no se necesitan)
-- ============================================================

-- Usuario administrador/registrador (email: js_8@gmail.com)
-- Nota: en producción usar generate_password_hash() de Werkzeug
INSERT INTO `usuarios` (`id`, `nombre`, `apellido`, `email`, `empresa`, `telefono`, `password`, `fecha_registro`)
VALUES (
    1,
    'Juan',
    'Sánchez',
    'js_8@gmail.com',
    'Mi Empresa',
    '3001234567',
    'pbkdf2:sha256:600000$...',
    CURRENT_TIMESTAMP
)
ON DUPLICATE KEY UPDATE `email` = `email`;

-- Usuario de prueba (email: maria@ejemplo.com)
INSERT INTO `usuarios` (`id`, `nombre`, `apellido`, `email`, `empresa`, `telefono`, `password`, `fecha_registro`)
VALUES (
    2,
    'María',
    'Gómez',
    'maria@ejemplo.com',
    'Otra Empresa',
    '3109876543',
    'pbkdf2:sha256:600000$...',
    CURRENT_TIMESTAMP
)
ON DUPLICATE KEY UPDATE `email` = `email`;

-- Mensajes de contacto de ejemplo
INSERT INTO `mensajes_contacto` (`id`, `nombre`, `email`, `mensaje`, `respuesta_admin`, `estado`, `fecha_registro`)
VALUES 
    (1, 'Carlos Ruiz', 'carlos@cliente.com', 'Hola, quiero información sobre sus productos.', NULL, 'nuevo', CURRENT_TIMESTAMP),
    (2, 'Ana Torres', 'ana@cliente.com', 'Tengo una duda sobre el envío a mi ciudad.', 'Claro, hacemos envíos a todo el país. ¿Cuál es tu ciudad?', 'respondido', CURRENT_TIMESTAMP),
    (3, 'Luis Pérez', 'luis@cliente.com', '¿Tienen soporte técnico?', NULL, 'atendido', CURRENT_TIMESTAMP)
ON DUPLICATE KEY UPDATE `email` = `email`;

SET FOREIGN_KEY_CHECKS = 1;