# RFI sintética

Conjunto de dados **100% fictício** para testar e avaliar o motor de respostas. Nenhum arquivo descreve um cliente, uma empresa ou um produto real.

## Arquivos

| Arquivo | O que é |
| --- | --- |
| `rfi_ficticia.xlsx` | Questionário de entrada: 30 perguntas (`id`, `pergunta`), no estilo das RFIs recebidas por chamado. Algumas foram escritas de propósito com erros e informalidade, como um cliente escreveria. |
| `gabarito.xlsx` | Resposta esperada por pergunta: `area_correta`, `tem_base_na_documentacao` (Sim/Não) e `artigo_fonte`. Usado pela avaliação da IA (`make eval`). |
| `documentacao/` | Base de conhecimento do produto fictício **AcmeJus**: 11 artigos curtos em Markdown (segurança, privacidade, backup, hospedagem, criptografia, acessos, vulnerabilidades, incidentes, mudanças, produto e suporte). |

## Áreas usadas

Segurança, Infraestrutura, Jurídico, Desenvolvimento, Produto, Suporte e Comercial.

## Lacunas propositais

Três perguntas **não têm resposta na documentação**, para testar se o motor marca "precisa de especialista" em vez de inventar:

| id | Pergunta |
| --- | --- |
| 7 | Supervisão das atividades de desenvolvimento realizadas por terceiros |
| 24 | Modelo de licenciamento e cobrança |
| 27 | Certificação ISO 27001 |

A pergunta 4 ("Quais controles de segurança estão implementados?") exige combinar vários artigos.

## Linha de base

Uma regra fixa por palavra-chave, testada em uma amostra de 5 perguntas, acertou a área em 2 (40%). Falhou com sinônimos ("cópia de segurança" em vez de "backup") e com perguntas que não citam nenhuma palavra-chave.
