path = r"c:\Users\johns\DEV\inventory\php-ddd-inventory\public\index.php"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

target = """set_exception_handler(function (Throwable $e): void {
    if (!headers_sent()) {
        http_response_code(500);
        header('Content-Type: application/json');
    }
    error_log('[UNHANDLED] ' . get_class($e) . ': ' . $e->getMessage()
        . ' in ' . $e->getFile() . ':' . $e->getLine());
    echo json_encode(['error' => 'Internal server error']);
    return;
});"""

replacement = """set_exception_handler(function (Throwable $e): void {
    if (!headers_sent()) {
        http_response_code(500);
        header('Content-Type: application/json');
    }
    @file_put_contents(__DIR__ . '/../storage/logs/server_error.log', '[UNHANDLED] ' . get_class($e) . ': ' . $e->getMessage() . " in " . $e->getFile() . ":" . $e->getLine() . "\\n" . $e->getTraceAsString() . "\\n", FILE_APPEND);
    echo json_encode(['error' => 'Internal server error', 'exception' => get_class($e), 'message' => $e->getMessage()]);
    return;
});"""

if target in content:
    content = content.replace(target, replacement)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated exception handler in public/index.php")
else:
    print("Target not found")
