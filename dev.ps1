<#
.SYNOPSIS
    Comandos de desenvolvimento do RFP Automation para PowerShell (equivalente ao Makefile).

.EXAMPLE
    .\dev.ps1 setup                       # primeira vez: .env, sobe tudo, migra e cria usuários de teste
    .\dev.ps1 up                          # sobe os serviços
    .\dev.ps1 test                        # testes do backend
    .\dev.ps1 migration -Mensagem "cadastros: clientes"
    .\dev.ps1 ajuda                       # lista os comandos

.NOTES
    Se o Windows bloquear a execução de scripts, rode uma vez:
        Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
    ou chame assim:
        powershell -ExecutionPolicy Bypass -File .\dev.ps1 up
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Comando = "ajuda",

    [string]$Mensagem
)

$ErrorActionPreference = "Stop"
# Erros aparecem como uma linha simples, sem o rastreamento do PowerShell.
trap {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
Set-Location -Path $PSScriptRoot

$Comandos = [ordered]@{
    "setup"            = "Primeira vez: cria o .env, sobe os servicos, migra e cria os usuarios de teste"
    "env"              = "Cria o .env a partir do .env.example (se ainda nao existir)"
    "up"               = "Sobe todos os servicos"
    "down"             = "Derruba os servicos (mantem os dados)"
    "logs"             = "Acompanha os logs (Ctrl+C para sair)"
    "ps"               = "Estado dos servicos"
    "migrate"          = "Aplica as migracoes do banco"
    "migration"        = "Cria uma migracao: .\dev.ps1 migration -Mensagem 'descricao'"
    "seed"             = "Cria os usuarios de teste (senha: rfp-local-123)"
    "test"             = "Testes do backend e do front"
    "test-integration" = "Testes com Postgres, Redis e worker reais"
    "lint"             = "ruff, mypy, import-linter e lint do front"
    "fmt"              = "Formata o codigo"
    "shell-api"        = "Abre um shell dentro do container da API"
    "ajuda"            = "Mostra esta lista"
}

function Invoke-Passo {
    # Executa um comando externo e para o script se ele falhar.
    param([Parameter(Mandatory)][string]$Exe, [string[]]$Argumentos = @())
    & $Exe @Argumentos
    if ($LASTEXITCODE -ne 0) {
        throw "Falhou ($LASTEXITCODE): $Exe $($Argumentos -join ' ')"
    }
}

$script:DockerOk = $false
function Invoke-Compose {
    param([string[]]$Argumentos)
    if (-not $script:DockerOk) { Test-Docker; $script:DockerOk = $true }
    Invoke-Passo "docker" (@("compose") + $Argumentos)
}
function Invoke-Api     { param([string[]]$Argumentos) Invoke-Compose (@("exec", "api") + $Argumentos) }
function Invoke-Front   { param([string[]]$Argumentos) Invoke-Compose (@("exec", "frontend") + $Argumentos) }

function Test-DockerEngine {
    # No Windows PowerShell 5.1, redirecionar a saida de erro de um programa com
    # ErrorActionPreference = Stop vira excecao. Por isso relaxamos so aqui.
    $anterior = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        docker info *> $null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    } finally {
        $ErrorActionPreference = $anterior
    }
}

function Find-DockerDesktop {
    $candidatos = @()
    if ($env:ProgramFiles) { $candidatos += Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe" }
    if ($env:LOCALAPPDATA) { $candidatos += Join-Path $env:LOCALAPPDATA "Docker\Docker Desktop.exe" }
    foreach ($c in $candidatos) {
        if (Test-Path -LiteralPath $c) { return $c }
    }
    return $null
}

function Test-Docker {
    param([int]$EsperaSegundos = 180)
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker nao encontrado. Instale o Docker Desktop: https://www.docker.com/products/docker-desktop/"
    }
    if (Test-DockerEngine) { return }

    $exe = Find-DockerDesktop
    if (-not $exe) {
        throw "O Docker Desktop nao esta rodando. Abra-o, espere aparecer 'Engine running' e tente de novo."
    }
    Write-Host "Docker Desktop fechado. Abrindo e aguardando o motor iniciar (pode levar 1 a 2 minutos)..." -NoNewline
    Start-Process -FilePath $exe | Out-Null
    $limite = (Get-Date).AddSeconds($EsperaSegundos)
    while ((Get-Date) -lt $limite) {
        Start-Sleep -Seconds 3
        Write-Host "." -NoNewline
        if (Test-DockerEngine) { Write-Host " ok"; return }
    }
    Write-Host ""
    throw ("O Docker Desktop nao ficou pronto em $EsperaSegundos s. Abra-o manualmente e confira: " +
        "1) se ele pede para aceitar os termos ou fazer login; " +
        "2) se o WSL 2 esta instalado (rode 'wsl --status' no PowerShell); " +
        "3) se a virtualizacao esta ativa na BIOS. Depois rode .\dev.ps1 setup de novo.")
}

function New-EnvFile {
    if (-not (Test-Path ".env")) {
        Copy-Item ".env.example" ".env"
        Write-Host "Criado .env a partir de .env.example"
    }
}

function Wait-Api {
    param([int]$Segundos = 90)
    Write-Host "Aguardando a API responder..." -NoNewline
    $limite = (Get-Date).AddSeconds($Segundos)
    while ((Get-Date) -lt $limite) {
        try {
            $r = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 3
            if ($r.StatusCode -eq 200) { Write-Host " ok"; return }
        } catch { }
        Start-Sleep -Seconds 2
        Write-Host "." -NoNewline
    }
    throw "A API nao respondeu em $Segundos s. Veja os logs com: .\dev.ps1 logs"
}

function Show-Enderecos {
    Write-Host ""
    Write-Host "Interface:  http://localhost:5173"
    Write-Host "API:        http://localhost:8000/api/docs"
    Write-Host "MinIO:      http://localhost:9001"
    Write-Host "Mailpit:    http://localhost:8025"
}

switch ($Comando.ToLower()) {
    "setup" {
        Test-Docker
        New-EnvFile
        Invoke-Compose @("up", "-d", "--build")
        Wait-Api
        Invoke-Api @("alembic", "upgrade", "head")
        Invoke-Api @("python", "-m", "app.seed")
        Show-Enderecos
        Write-Host ""
        Write-Host "Entre com admin@rfp.local / rfp-local-123 (ou analista@, validador@, conhecimento@)."
    }
    "env" { New-EnvFile }
    "up" {
        Test-Docker
        New-EnvFile
        Invoke-Compose @("up", "-d", "--build")
        Show-Enderecos
    }
    "down"      { Invoke-Compose @("down") }
    "logs"      { Invoke-Compose @("logs", "-f", "--tail=100") }
    "ps"        { Invoke-Compose @("ps") }
    "migrate"   { Invoke-Api @("alembic", "upgrade", "head") }
    "migration" {
        if (-not $Mensagem) { throw "Informe a descricao: .\dev.ps1 migration -Mensagem 'cadastros: clientes'" }
        Invoke-Api @("alembic", "revision", "--autogenerate", "-m", $Mensagem)
    }
    "seed"      { Invoke-Api @("python", "-m", "app.seed") }
    "test" {
        Invoke-Api @("env", "REQUIRE_DB=1", "pytest")
        Invoke-Front @("pnpm", "test")
    }
    "test-integration" {
        Invoke-Api @("env", "REQUIRE_DB=1", "RUN_INTEGRATION=1", "CELERY_WORKER=1", "pytest", "-m", "integration")
    }
    "lint" {
        Invoke-Api @("ruff", "check", ".")
        Invoke-Api @("ruff", "format", "--check", ".")
        Invoke-Api @("mypy", "app")
        Invoke-Api @("lint-imports")
        Invoke-Front @("pnpm", "run", "lint")
    }
    "fmt" {
        Invoke-Api @("ruff", "check", "--fix", ".")
        Invoke-Api @("ruff", "format", ".")
        Invoke-Front @("pnpm", "run", "format")
    }
    "shell-api" { docker compose exec api bash }
    { $_ -in @("ajuda", "help", "-h", "--help") } {
        Write-Host "Uso: .\dev.ps1 <comando>"
        Write-Host ""
        foreach ($c in $Comandos.Keys) { Write-Host ("  {0,-18} {1}" -f $c, $Comandos[$c]) }
    }
    default {
        Write-Host "Comando desconhecido: $Comando" -ForegroundColor Red
        Write-Host "Use .\dev.ps1 ajuda para ver a lista."
        exit 1
    }
}
