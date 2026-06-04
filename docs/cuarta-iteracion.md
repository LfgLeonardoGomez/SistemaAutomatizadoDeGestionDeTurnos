# **Desarrollo de un Sistema SaaS para la Automatización de la Gestión de Turnos Odontológicos mediante la Integración de Bots de Mensajería e Inteligencia de Calendario**

### **Carrera:** Tecnicatura Universitaria en Programación

### **Institución:** Universidad Tecnológica Nacional (UTN) - FRM

### Integrantes del Proyecto:

### Fausto Chirino

### Sebastian Saez

### Leonardo Gómez

### Neyén Bianchi

### **Director del Proyecto:** Alberto Cortez

### **Argentina - Mendoza** 2026

**Resumen**:

En la actualidad, la gestión de turnos en el ámbito de la salud continúa
siendo, en muchos casos, un proceso manual, ineficiente y propenso a
errores. Profesionales y centros de atención enfrentan diariamente
problemáticas como la alta tasa de ausencias de pacientes, la sobrecarga
administrativa y la dificultad para reorganizar agendas ante
cancelaciones de último momento.

Paralelamente, los pacientes demandan cada vez más inmediatez,
simplicidad y canales de comunicación accesibles, siendo las
aplicaciones de mensajería instantánea uno de los medios más utilizados
para la interacción cotidiana.

En este contexto, surge la necesidad de desarrollar una solución
tecnológica que permita automatizar la gestión de turnos, optimizar la
organización del profesional y mejorar la experiencia del paciente.

El presente proyecto propone el desarrollo de una plataforma SaaS
orientada a la automatización de la gestión de turnos odontológicos. La
solución se basa en la integración de herramientas como Telegram para la
interacción con los usuarios, Google Calendar para la administración de
la agenda y un conjunto de servicios backend que permiten la ejecución
de acciones automatizadas tales como confirmaciones, recordatorios,
cancelaciones y reprogramaciones de turnos.

De esta manera, se busca reducir la carga operativa del profesional,
minimizar la tasa de ausencias y brindar una experiencia más eficiente,
ágil y accesible para los pacientes.

[**CAPÍTULO 1: Introducción**](#capítulo-1-introducción) 6

> [1.1 Contexto del problema](#contexto-del-problema) 6
>
> [1.2 Planteamiento del problema](#planteamiento-del-problema) 6
>
> [1.3 Justificación](#justificación) 6
>
> [1.4 Objetivo general](#objetivo-general) 7
>
> [1.5 Objetivos específicos](#objetivos-específicos) 7
>
> [1.6 Alcance y limitaciones](#alcance-y-limitaciones) 7
>
> [**CAPÍTULO 2: Marco Teórico**](#capítulo-2-marco-teórico) 7
>
> [2.1 Sistemas de gestión de turnos](#sistemas-de-gestión-de-turnos) 8
>
> [2.2 Automatización de procesos](#automatización-de-procesos) 8
>
> [2.3 Arquitectura basada en
> servicios](#arquitectura-basada-en-servicios) 8
>
> [2.4 APIs y comunicación entre
> sistemas](#apis-y-comunicación-entre-sistemas) 8
>
> [2.5 Aplicaciones de mensajería como interfaz de
> usuario](#aplicaciones-de-mensajería-como-interfaz-de-usuario) 9
>
> [2.6 n8n como herramienta de
> automatización](#n8n-como-herramienta-de-automatización) 9
>
> [2.7 Backend con FastAPI](#backend-con-fastapi) 10
>
> [2.8 Bases de datos relacionales:
> PostgreSQL](#bases-de-datos-relacionales-postgresql) 10
>
> [2.9 Integración con servicios de
> calendario](#integración-con-servicios-de-calendario) 10
>
> [2.10 Planificación de tareas con
> Scheduler](#planificación-de-tareas-con-scheduler) 11
>
> [2.11 Modelo SaaS (Software as a
> Service)](#modelo-saas-software-as-a-service) 11
>
> [**CAPÍTULO 3: Marco Metodológico**](#capítulo-3-marco-metodológico)
> 11
>
> [3.1 Tipo de investigación](#tipo-de-investigación) 11
>
> [3.2 Enfoque metodológico](#enfoque-metodológico) 12
>
> [3.3 Diseño de investigación](#diseño-de-investigación) 12
>
> [3.4 Técnicas de recolección de
> datos](#técnicas-de-recolección-de-datos) 12
>
> [3.5 Herramientas utilizadas](#herramientas-utilizadas) 12
>
> [**CAPÍTULO 4: Desarrollo de la
> Investigación**](#capítulo-4-desarrollo-de-la-investigación) 13
>
> [4.1 Modelo de Datos (Modelo ER
> Final)](#modelo-de-datos-modelo-er-final) 13
>
> [4.2 Reglas de Negocio](#reglas-de-negocio) 14
>
> [4.3 Arquitectura del Sistema](#arquitectura-del-sistema) 14
>
> [4.3.1 Descripción general](#descripción-general) 14
>
> [4.3.2 Componentes principales](#componentes-principales) 15
>
> [4.3.3 Flujo de interacción](#flujo-de-interacción) 16
>
> [4.4 Definición de Requerimientos](#definición-de-requerimientos) 16
>
> [4.4.1 Requerimientos Funcionales](#requerimientos-funcionales) 16
>
> [4.4.2 Requerimientos No Funcionales](#requerimientos-no-funcionales)
> 17
>
> [4.5 Flujos e Integraciones del
> Sistema](#flujos-e-integraciones-del-sistema) 18
>
> [4.5.1 Flujo de Reserva de Turno](#flujo-de-reserva-de-turno) 18
>
> [4.5.2 Flujo de Cancelación](#flujo-de-cancelación) 19
>
> [4.5.3 Flujo de Reprogramación](#flujo-de-reprogramación) 19
>
> [4.5.4 Flujo de Recordatorio](#flujo-de-recordatorio) 20
>
> [4.5.5 Flujo de Lista de Espera](#flujo-de-lista-de-espera) 20
>
> [4.5.6 Integraciones del Sistema](#integraciones-del-sistema) 21
>
> [4.5.6.1 Integración con Telegram](#integración-con-telegram) 21
>
> [4.5.6.2 Integración con Google
> Calendar](#integración-con-google-calendar) 21
>
> [4.5.6.3 Procesos Automáticos
> (Scheduler)](#procesos-automáticos-scheduler) 22
>
> [**CAPÍTULO 5 : Resultados y
> Pruebas**](#capítulo-5-resultados-y-pruebas) 23
>
> [5.2 Estrategia de validación](#estrategia-de-validación) 23
>
> [5.3 Casos de Prueba](#casos-de-prueba) 23
>
> [Caso 1: Reserva de turno exitosa](#caso-1-reserva-de-turno-exitosa)
> 23
>
> [Caso 2: Expiración de reserva
> temporal](#caso-2-expiración-de-reserva-temporal) 24
>
> [Caso 3: Cancelación de turno](#caso-3-cancelación-de-turno) 25
>
> [Caso 4: Reprogramación de turno](#caso-4-reprogramación-de-turno) 26
>
> [Caso 5: Recordatorio automático](#caso-5-recordatorio-automático) 26
>
> [Caso 6: Lista de espera](#caso-6-lista-de-espera) 27
>
> [**CAPÍTULO 6: Conclusiones y Trabajo
> Futuro**](#capítulo-6-conclusiones-y-trabajo-futuro) 28
>
> [6.2 Aportes del trabajo](#aportes-del-trabajo) 29
>
> [6.3 Limitaciones](#limitaciones) 29
>
> [6.4 Trabajo futuro](#trabajo-futuro) 29

**\**

Palabras clave: Automatización, Gestión de turnos, Bots de mensajería,
Inteligencia artificial, SaaS, Calendario, Odontología, n8n

## **CAPÍTULO 1: Introducción** 

### 1.1 Contexto del problema

En la actualidad, la gestión de turnos en el ámbito de la salud,
particularmente en consultorios odontológicos, continúa realizándose en
muchos casos mediante procesos manuales o herramientas poco integradas.
Esta situación genera ineficiencias operativas, dificultades en la
organización de la agenda y una alta dependencia de la intervención
humana para tareas repetitivas.\
Asimismo, el crecimiento en el uso de aplicaciones de mensajería
instantánea ha modificado las expectativas de los pacientes, quienes
demandan canales de comunicación más ágiles, accesibles y disponibles en
todo momento.

### 1.2 Planteamiento del problema

La gestión tradicional de turnos médicos presenta múltiples
inconvenientes tanto para los profesionales como para los pacientes.\
Por un lado, los profesionales enfrentan pérdida de tiempo en la
coordinación manual de turnos, alta tasa de inasistencia, dificultad
para reorganizar cancelaciones, falta de métricas sobre su actividad y
una fuerte dependencia de los asistentes administrativos.\
Por otro lado, los pacientes experimentan dificultades para conseguir
turnos de manera rápida, falta de confirmaciones claras, olvido de citas
y escasa flexibilidad para reprogramar.

### 1.3 Justificación

La automatización del proceso de gestión de turnos permite reducir la
carga operativa del profesional, optimizar el uso del tiempo y mejorar
la organización de la agenda.\
Asimismo, la implementación de recordatorios automáticos y mecanismos de
confirmación contribuye a disminuir la tasa de ausencias.\
Desde la perspectiva del paciente, una solución basada en mensajería
instantánea mejora la accesibilidad, la rapidez en la obtención de
turnos y la experiencia general del servicio.

### 1.4 Objetivo general

Desarrollar una plataforma SaaS que permita automatizar la gestión de
turnos odontológicos mediante el uso de aplicaciones de mensajería y
herramientas de integración.

### 1.5 Objetivos específicos

El proyecto consiste en diseñar un sistema de interacción con usuarios a
través de aplicaciones de mensajería como Telegram, que permita
gestionar de forma automatizada todo el ciclo de vida de los turnos:
desde su creación y confirmación hasta la cancelación y reprogramación.
La solución se integrará con servicios de calendario para administrar la
agenda y evitar la pérdida de turnos en casos de ausentismo, y contará
con mecanismos de recordatorios automáticos orientados a reducir las
inasistencias. Toda la información de turnos y pacientes será almacenada
y gestionada mediante una base de datos estructurada.

### 1.6 Alcance y limitaciones

El proyecto se centra en el desarrollo de una solución orientada a la
automatización de la gestión de turnos en consultorios odontológicos
pequeños de un solo profesional, utilizando herramientas como mensajería
instantánea, servicios de calendario y automatización de procesos, lo
que puede generar una dependencia de servicios externos (por ejemplo si
una api no se encuentra disponible por una caida momentanea).

No se contempla la implementación en entornos hospitalarios de gran
escala ni la integración con sistemas clínicos complejos, limitándose a
un entorno controlado para la validación del sistema.

## **CAPÍTULO 2: Marco Teórico**

### 2.1 Sistemas de gestión de turnos

Los sistemas de gestión de turnos son soluciones informáticas diseñadas
para administrar la asignación de citas entre profesionales y pacientes.
Su objetivo principal es optimizar el uso del tiempo, reducir errores
humanos y mejorar la organización de la agenda.

Tradicionalmente, estos sistemas han sido implementados de forma manual
o mediante herramientas aisladas, lo que limita su eficiencia. En los
últimos años, la tendencia ha evolucionado hacia soluciones digitales
que incorporan automatización, integración con calendarios y
comunicación directa con los usuarios.

### 2.2 Automatización de procesos

La automatización de procesos consiste en el uso de tecnologías para
ejecutar tareas repetitivas sin intervención humana. En el contexto de
la gestión de turnos, esto se traduce en la capacidad de realizar
acciones como la confirmación automática de citas, el envío de
recordatorios, la reprogramación de turnos y la gestión de
cancelaciones. De esta manera, la automatización no solo reduce la carga
operativa, sino que también mejora la precisión y la eficiencia del
sistema.

### 2.3 Arquitectura basada en servicios

El sistema propuesto se basa en una arquitectura desacoplada, donde
diferentes componentes cumplen funciones específicas y se comunican
entre sí mediante interfaces bien definidas. Este enfoque permite
alcanzar una mayor escalabilidad del sistema y facilita tanto su
mantenimiento como la separación de responsabilidades entre sus partes.
Además, simplifica la integración con servicios externos, haciendo que
el conjunto sea más flexible y adaptable a futuros cambios.

### 2.4 APIs y comunicación entre sistemas

Una API permite la comunicación entre distintos sistemas de software, y
en este proyecto cumple un rol fundamental en la integración de
múltiples servicios. A través de ellas se interactuará con plataformas
de mensajería, se gestionarán eventos en calendarios y se conectará el
backend con otros servicios externos. Este enfoque basado en APIs
permite construir una solución modular y extensible, capaz de adaptarse
y crecer junto con las necesidades del sistema.

### 2.5 Aplicaciones de mensajería como interfaz de usuario

Las aplicaciones de mensajería instantánea se han convertido en un canal
de comunicación ampliamente adoptado, y su uso como interfaz de usuario
en sistemas informáticos ofrece ventajas significativas: permite una
interacción natural mediante texto, garantiza la accesibilidad desde
dispositivos móviles y elimina la necesidad de instalar aplicaciones
adicionales. En este proyecto, la mensajería se utiliza como medio
principal de interacción entre el sistema y el usuario, facilitando la
gestión de turnos de manera simple e inmediata.

### 2.6 n8n como herramienta de automatización

n8n es una herramienta de automatización de flujos de trabajo que
permite integrar diferentes servicios mediante la creación de procesos
visuales. Su funcionamiento se basa en el diseño de flujos mediante
nodos, lo que facilita tanto la integración con APIs como la ejecución
de tareas automatizadas, ofreciendo además la flexibilidad necesaria
para adaptar la lógica de negocio a distintos escenarios. En este
sistema, n8n actúa como orquestador de procesos, gestionando la lógica
de automatización y la comunicación entre los distintos servicios que
componen la solución.

### 2.7 Backend con FastAPI

FastAPI es un framework moderno para el desarrollo de APIs en Python,
caracterizado por su alto rendimiento y facilidad de uso. Entre sus
principales ventajas se destacan la alta velocidad de ejecución, la
validación automática de datos, la documentación automática de endpoints
y el soporte para programación asíncrona. En este proyecto, el backend
desarrollado con FastAPI se encarga de la lógica de negocio, la gestión
de datos y la exposición de servicios para el resto del sistema.

### 2.8 Bases de datos relacionales: PostgreSQL

PostgreSQL es un sistema de gestión de bases de datos relacional
ampliamente utilizado por su robustez y confiabilidad. Permite el
almacenamiento estructurado de datos con integridad referencial, la
ejecución de consultas complejas mediante SQL y una escalabilidad
adecuada para distintos volúmenes de información. En este proyecto, se
utiliza para almacenar toda la información relacionada con usuarios,
turnos y configuraciones del sistema.

### 2.9 Integración con servicios de calendario

Los servicios de calendario permiten gestionar eventos temporales de
manera estructurada. Su integración en el sistema facilita la
visualización de la agenda, la sincronización de turnos y la prevención
de conflictos de horarios. El uso de herramientas como Google Calendar
permite aprovechar funcionalidades ya existentes y consolidadas,
mejorando así la gestión del tiempo de forma eficiente.

### 2.10 Planificación de tareas con Scheduler

Un scheduler es un componente que permite ejecutar tareas en momentos
específicos o de forma periódica. En este sistema, se emplea para enviar
recordatorios antes de los turnos, ejecutar validaciones programadas y
automatizar procesos dependientes del tiempo. Su incorporación resulta
clave para garantizar el correcto funcionamiento de las notificaciones y
la gestión temporal del sistema en su conjunto.

### 2.11 Modelo SaaS (Software as a Service)

El modelo SaaS consiste en ofrecer software como un servicio accesible a
través de internet, sin necesidad de instalación local. Sus principales
ventajas radican en la posibilidad de acceder desde cualquier
dispositivo, contar con actualizaciones centralizadas, escalar según la
demanda y reducir los costos de implementación. El sistema propuesto se
enmarca dentro de este modelo, permitiendo su utilización por distintos
profesionales sin que estos requieran infraestructura propia.

.

## **CAPÍTULO 3: Marco Metodológico**

### 3.1 Tipo de investigación

La investigación es de tipo aplicada, ya que tiene como objetivo
desarrollar una solución tecnológica concreta para resolver un problema
real en la gestión de turnos odontológicos.

Asimismo, presenta un carácter descriptivo, debido a que se analizan los
procesos actuales de gestión de turnos y se identifican sus principales
limitaciones con el fin de proponer mejoras mediante la automatización.

### 3.2 Enfoque metodológico

El enfoque adoptado es de tipo mixto.

Por un lado, se emplea un enfoque cualitativo para analizar las
problemáticas existentes en la gestión de turnos, considerando la
experiencia tanto de profesionales como de pacientes.

Por otro lado, se incorpora un enfoque cuantitativo mediante la
evaluación del comportamiento del sistema desarrollado, a través de
métricas como la reducción de inasistencias, tiempos de respuesta y
eficiencia en la asignación de turnos.

### 

### 3.3 Diseño de investigación

Se adopta un diseño basado en desarrollo tecnológico con validación
mediante caso de uso.

El estudio se centra en la implementación de un sistema funcional que
automatiza la gestión de turnos odontológicos, utilizando herramientas
de mensajería, servicios de calendario y automatización de procesos.

La validación del sistema se realiza en un entorno controlado, simulando
la operatoria de un consultorio odontológico, lo que permite evaluar su
funcionamiento, identificar mejoras y verificar el cumplimiento de los
objetivos planteados.

### 3.4 Técnicas de recolección de datos

• Análisis de procesos actuales de gestión de turnos en consultorios
odontológicos.

• Contacto con un profesional que nos planteó el problema.

### 3.5 Herramientas utilizadas

• n8n para la automatización de flujos de trabajo e integración entre
servicios.

• FastAPI para el desarrollo del backend y la lógica de negocio.

• PostgreSQL como sistema de gestión de base de datos.

• API de Telegram para la interacción con los usuarios mediante
mensajería.

• Google Calendar API para la gestión y sincronización de turnos.

• APScheduler para la ejecución de tareas programadas (recordatorios y
validaciones).

## **CAPÍTULO 4: Desarrollo de la Investigación**

Este capítulo describe el entorno de prueba y el desarrollo del sistema
de gestión automatizada de turnos odontológicos, incluyendo el modelo de
datos, las reglas de negocio, la arquitectura del sistema y el flujo de
interacción entre componentes.

### 4.1 Modelo de Datos (Modelo ER Final)

El sistema se basa en un modelo relacional estructurado que garantiza la
consistencia, integridad y eficiencia en la gestión de turnos.

**Entidades principales:**

**👤 Paciente**

- id

- nombre

- apellido

- dni

- telefono

- creado_en

**👨‍⚕️ Profesional**

- id

- nombre

- especialidad

- duracion_turno

- horario_inicio

- horario_fin

- dias_atencion

**📅 Turno (entidad central)**

- id

- fecha

- hora_inicio

- hora_fin

- estado

- paciente_id

- profesional_id

- creado_en

**⏳ ReservaTemporal**

- id

- turno_id

- expiracion

**Relaciones:**

- Paciente → 1:N → Turnos

- Profesional → 1:N → Turnos

**Justificación:\**
La información correspondiente a la última atención del paciente se
obtiene dinámicamente a partir de los turnos registrados, evitando
redundancia de datos y garantizando consistencia. Las consultas
indexadas sobre la entidad Turno permiten obtener la última visita de
manera eficiente.

### 4.2 Reglas de Negocio

**Regla 1:** Un paciente solo puede tener un turno activo.\
**Regla 2:** Los turnos completados forman el historial del paciente.\
**Regla 3:** La reserva temporal expira automáticamente si no se
confirma.\
**Regla 4:** La cancelación libera el turno para otros pacientes.\
**Regla 5:** La reprogramación se gestiona como cancelación seguida de
nueva reserva.

**Justificación:\**
Estas reglas garantizan la consistencia de la agenda, previenen
conflictos de turnos y optimizan la experiencia del paciente. La
implementación de recordatorios automáticos 24 horas antes de cada turno
contribuye a reducir la tasa de ausencias, asegurando un sistema más
eficiente.

### 4.3 Arquitectura del Sistema

### **4.3.1 Descripción general**

El sistema se estructura bajo una arquitectura cliente-servidor, donde
la interacción del usuario se realiza a través de un bot de Telegram,
mientras que la lógica de negocio se centraliza en un backend
desarrollado con FastAPI, encargado de la gestión de turnos, integración
con servicios externos y persistencia de datos.

### 

### 4.3.2 Componentes principales

**1. Telegram Bot**

- Punto de entrada del sistema.

- Interfaz conversacional con el usuario.

- Gestiona:

  - Flujo de reserva

  - Confirmaciones

  - Cancelaciones

- Envía requests al backend (FastAPI).

**2. Backend (FastAPI)**

- Núcleo del sistema.

- Responsabilidades:

  - Lógica de negocio y validaciones

  - Gestión de turnos y control de estados

  - Integración con la base de datos y Google Calendar

**3. Base de Datos (PostgreSQL)**

- Almacena:

  - Pacientes

  - Turnos

  - Configuración del profesional

  - Estados del sistema

- Seleccionada por su robustez, soporte de consultas complejas y manejo
  eficiente de concurrencia.

**4. Google Calendar API**

- Función: Crear, actualizar y eliminar eventos

- Actúa como "agenda espejo" del sistema.

**5. Scheduler (dentro de FastAPI, APScheduler)**

- Responsable de:

  - Recordatorios automáticos 24 horas antes del turno

  - Liberación de reservas temporales vencidas

  - Notificaciones automáticas a pacientes

### **4.3.3 Flujo de interacción**

1.  El usuario solicita un turno mediante Telegram.

2.  Telegram envía la solicitud al backend (FastAPI).

3.  FastAPI:

    - Consulta la base de datos

    - Válida reglas de negocio

    - Interactúa con Google Calendar

4.  La respuesta se envía de vuelta al usuario vía Telegram.

Este flujo asegura que todas las acciones estén centralizadas, sean
consistentes y cumplan con las reglas de negocio definidas.

### 4.4 Definición de Requerimientos

En esta sección se presentan los requerimientos funcionales y no
funcionales del sistema, los cuales guían el desarrollo, garantizan el
cumplimiento de las reglas de negocio y aseguran la experiencia adecuada
tanto para profesionales como para pacientes.

### 4.4.1 Requerimientos Funcionales

**1. Gestión de turnos**

- Permitir a los pacientes solicitar turnos mediante interacción en
  Telegram.

- Mostrar disponibilidad de fechas y horarios en tiempo real.

- Permitir la selección de turnos disponibles de forma intuitiva.

**2. Gestión de pacientes**

- Registrar información de los pacientes (nombre, apellido, DNI,
  teléfono).

- Identificar usuarios recurrentes automáticamente.

- Permitir la reserva de turnos a nombre de terceros cuando sea
  necesario.

**3. Gestión del ciclo de turnos**

- Confirmar los turnos seleccionados por los usuarios.

- Permitir la cancelación de turnos de manera sencilla.

- Permitir la reprogramación de turnos siguiendo las reglas de negocio.

- Gestionar los estados del turno: disponible, reservado, confirmado,
  cancelado y completado.

**4. Reserva temporal**

- Bloquear temporalmente un turno durante el proceso de reserva para
  evitar conflictos.

- Liberar automáticamente el turno si no se confirma en el tiempo
  definido.

**5. Recordatorios automáticos**

- Enviar notificaciones 24 horas antes del turno.

- Permitir que el paciente confirme, cancele o reprograme directamente
  desde el mensaje recibido.

**6. Integración con calendario**

- Crear eventos en Google Calendar al confirmar un turno.

- Actualizar o eliminar eventos automáticamente ante modificaciones o
  cancelaciones.

**7. Gestión de información**

- Permitir al profesional consultar los turnos programados para el día.

- Generar métricas básicas de uso del sistema, como número de turnos por
  día o tasa de confirmación.

**8. Lista de espera**

- Registrar pacientes en lista de espera cuando no haya turnos
  disponibles.

- Notificar automáticamente la disponibilidad de turnos ante
  cancelaciones.

- Asignar turnos liberados de forma automática a pacientes en lista de
  espera.

### 4.4.2 Requerimientos No Funcionales

**1. Rendimiento**

- El sistema deberá responder en tiempos adecuados a las solicitudes de
  los usuarios.

- Las consultas a la base de datos deberán estar optimizadas mediante
  índices y buenas prácticas de modelado.

**2. Seguridad**

- Proteger los datos personales de los pacientes según normas de
  confidencialidad.

- Validar la información ingresada por los usuarios para garantizar
  integridad y consistencia.

**3. Escalabilidad**

- Permitir la incorporación de nuevos profesionales sin afectar el
  funcionamiento actual.

- Adaptarse potencialmente a otros rubros o tipos de servicios de salud.

**4. Disponibilidad**

- El sistema deberá estar operativo durante los horarios de atención
  definidos por cada profesional.

**5. Usabilidad**

- Ofrecer una interfaz conversacional simple, intuitiva y guiada.

- Facilitar la interacción del usuario mediante pasos claros en la
  reserva, confirmación y modificación de turnos.

### 4.5 Flujos e Integraciones del Sistema

Los flujos e integraciones describen cómo los usuarios interactúan con
la plataforma y cómo las entidades del sistema cambian de estado durante
la gestión de turnos, así como la conexión con servicios externos que
permiten automatizar la operación.

### 4.5.1 Flujo de Reserva de Turno

**Descripción:\**
Este flujo permite a un paciente solicitar y confirmar un turno a través
del bot de Telegram, asegurando la disponibilidad y consistencia en la
gestión de turnos.

**Secuencia de acciones:**

1.  El usuario inicia la solicitud de turno.

2.  El sistema solicita la selección de una fecha disponible.

3.  El sistema muestra los horarios disponibles para la fecha
    seleccionada.

4.  El usuario selecciona un horario.

5.  El sistema crea una **reserva temporal** (RESERVADO_TEMPORAL).

6.  El sistema solicita los datos del paciente.

7.  El usuario ingresa los datos.

8.  El usuario confirma el turno.

9.  El sistema:

    - Cambia el estado a CONFIRMADO.

    - Crea el evento en Google Calendar.

    - Envía confirmación al usuario vía Telegram.

**Caso alternativo:\**
Si el usuario no confirma en el tiempo establecido, el turno vuelve
automáticamente a estado DISPONIBLE.

### 4.5.2 Flujo de Cancelación

**Secuencia de acciones:**

1.  El usuario solicita cancelar un turno.

2.  El sistema valida la existencia del turno.

3.  El sistema:

    - Cambia el estado a CANCELADO.

    - Elimina el evento correspondiente en Google Calendar.

4.  El turno vuelve a estar disponible mediante recalculo dinámico de
    horarios.

**Justificación:\**
El turno cancelado mantiene registro histórico en el sistema, mientras
que la disponibilidad del horario es recalculada para ofrecerlo a otros
pacientes.

### 4.5.3 Flujo de Reprogramación

**Secuencia de acciones:**

1.  El usuario solicita reprogramar un turno.

2.  El sistema muestra nuevas disponibilidades.

3.  El usuario selecciona un nuevo horario.

4.  El sistema:

    - Cancela el turno anterior (CANCELADO).

    - Crea un nuevo turno (CONFIRMADO).

    - Actualiza el evento en Google Calendar.

5.  El horario anterior vuelve a estar disponible mediante recalculo.

### 4.5.4 Flujo de Recordatorio

**Secuencia de acciones:**

1.  El scheduler detecta turnos programados en las próximas 24 horas.

2.  El sistema envía recordatorio al paciente vía Telegram.

3.  El paciente puede responder:

    - **Confirmar:** mantiene el estado CONFIRMADO.

    - **Cancelar:** pasa a CANCELADO.

    - **Reprogramar:** se ejecuta el flujo de reprogramación.

**Justificación:\**
El envío automático de recordatorios reduce la tasa de ausencias y
optimiza la gestión del tiempo del profesional.

### 4.5.5 Flujo de Lista de Espera

**Secuencia de acciones:**

1.  Un turno es cancelado.

2.  El sistema detecta pacientes registrados en la lista de espera.

3.  Se envía notificación automática al primer paciente disponible.

4.  El paciente que acepta:

    - Reserva el turno y pasa a CONFIRMADO.

**Consideración técnica:\**
La disponibilidad se calcula como:\
Horarios posibles MINUS turnos CONFIRMADOS o RESERVADOS.

### 4.5.6 Integraciones del Sistema

### 4.5.6.1 Integración con Telegram

**Rol dentro del sistema:\**
Telegram actúa como el **canal principal de interacción con el
usuario**, permitiendo solicitar, confirmar, cancelar o reprogramar
turnos, así como recibir recordatorios.

**Flujo técnico:**

1.  El usuario envía un mensaje al bot.

2.  Telegram envía un **webhook** al backend (FastAPI).

3.  FastAPI procesa el mensaje según el flujo actual del usuario.

4.  El backend ejecuta la lógica de negocio correspondiente y envía la
    respuesta al usuario.

**Ejemplo de webhook recibido:**

{

\"message\": {

\"from\": {\"id\": 123456, \"first_name\": \"Juan\"},

\"text\": \"Quiero un turno\"

}

}

**Justificación:\**
El uso de Telegram proporciona una interfaz accesible, evitando la
necesidad de desarrollar una aplicación propia y reduciendo la barrera
de entrada para los pacientes.

### 4.5.6.2 Integración con Google Calendar

**Rol dentro del sistema:\**
Google Calendar funciona como **agenda sincronizada**, reflejando todos
los turnos confirmados y facilitando la visualización de la programación
para profesionales.

**Flujos de integración:**

- **Confirmación de turno:**

  1.  Usuario confirma turno.

  2.  Backend genera evento en Google Calendar.

  3.  Se almacena referencia al evento para futuras modificaciones.

- **Cancelación:**

  1.  Turno pasa a CANCELADO.

  2.  Se elimina el evento del calendario.

- **Reprogramación:**

  1.  Se elimina el evento anterior.

  2.  Se crea un nuevo evento con el horario actualizado.

**Ejemplo técnico de creación de evento:**

{

\"summary\": \"Consulta médica\",

\"start\": {\"dateTime\": \"2026-04-10T10:00:00\"},

\"end\": {\"dateTime\": \"2026-04-10T10:30:00\"}

}

**Justificación:\**
Delegar la gestión de la agenda en Google Calendar permite aprovechar
una herramienta robusta y ampliamente utilizada, evitando el desarrollo
de un calendario propio y asegurando consistencia en los horarios.

### 4.5.6.3 Procesos Automáticos (Scheduler)

**Rol dentro del sistema:\**
El scheduler permite ejecutar tareas programadas sin intervención del
usuario.

**Funcionalidades:**

- Envío de recordatorios 24 horas antes del turno.

- Liberación de reservas temporales vencidas.

- Activación de lista de espera ante cancelaciones.

**Flujo de recordatorio:**

1.  El sistema detecta turnos próximos.

2.  Envía notificación al paciente.

3.  Espera respuesta: confirmar, cancelar o reprogramar.

**Justificación:\**
Los procesos automáticos optimizan la eficiencia operativa del sistema,
reduciendo la intervención manual del profesional y garantizando la
correcta gestión de turnos.

## **CAPÍTULO 5 : Resultados y Pruebas**

En este capítulo se presentan los resultados obtenidos a partir de la
implementación del sistema propuesto, junto con la validación de sus
funcionalidades mediante la ejecución de casos de prueba que simulan
escenarios reales de uso.

El objetivo es verificar el correcto funcionamiento de los procesos
principales, así como la coherencia entre los requerimientos definidos y
el comportamiento del sistema.

### 5.2 Estrategia de validación

La validación del sistema se realizó mediante **casos de prueba**, los
cuales reproducen situaciones típicas en la gestión de turnos médicos.

Cada caso de prueba incluye:

> ● Descripción del escenario
>
> ● Pasos ejecutados
>
> ● Resultado esperado
>
> ● Resultado obtenido

### 5.3 Casos de Prueba

## Caso 1: Reserva de turno exitosa

### Descripción

Un usuario solicita un turno y completa correctamente el proceso de
reserva.

### Pasos

1.  Usuario envía mensaje: *"Quiero un turno"*

2.  Sistema responde con fechas disponibles

3.  Usuario selecciona fecha

4.  Sistema muestra horarios

5.  Usuario selecciona horario

6.  Sistema genera RESERVADO_TEMPORAL

7.  Usuario ingresa datos

8.  Usuario confirma

### Resultado esperado

- Turno en estado CONFIRMADO

- Evento creado en Google Calendar

- Confirmación enviada al usuario

### Simulación (Telegram)

Usuario: Quiero un turno\
Bot: Seleccioná una fecha disponible:

- 10/04

- 11/04

Usuario: 10/04\
Bot: Horarios disponibles:

- 10:00

- 10:30

Usuario: 10:00\
Bot: Ingresá tus datos:\
Nombre, Apellido, DNI

Usuario: Juan Perez 12345678\
Bot: Confirmar turno para el 10/04 a las 10:00? (SI/NO)

Usuario: SI\
Bot: ✅ Turno confirmado correctamente

### Resultado obtenido

✔ Turno almacenado en base de datos\
✔ Estado: CONFIRMADO\
✔ Evento generado en Google Calendar

## Caso 2: Expiración de reserva temporal

### Descripción

El usuario no confirma el turno dentro del tiempo límite.

### Pasos

1.  Usuario selecciona turno

2.  Sistema lo marca como RESERVADO_TEMPORAL

3.  Usuario no responde

### Resultado esperado

- Turno deja de estar reservado

- Vuelve a disponibilidad lógica

### Simulación

Bot: Tenés 2 minutos para confirmar el turno

*(Usuario no responde)*

Bot: ⌛ El turno fue liberado por inactividad

### Resultado obtenido

✔ Reserva eliminada\
✔ Horario disponible nuevamente

## Caso 3: Cancelación de turno

### Descripción

Un paciente cancela un turno previamente confirmado.

### Pasos

1.  Usuario solicita cancelación

2.  Sistema procesa solicitud

### Resultado esperado

- Turno pasa a CANCELADO

- Evento eliminado del calendario

- Horario vuelve a estar disponible

### Simulación

Usuario: Cancelar turno\
Bot: ¿Confirmás la cancelación del turno del 10/04 a las 10:00? (SI/NO)

Usuario: SI\
Bot: ❌ Turno cancelado correctamente

### Resultado obtenido

✔ Estado actualizado a CANCELADO\
✔ Evento eliminado\
✔ Horario disponible para nuevos turnos

## Caso 4: Reprogramación de turno

### Descripción

El usuario cambia la fecha/hora de su turno.

### Pasos

1.  Usuario solicita reprogramación

2.  Sistema muestra disponibilidad

3.  Usuario selecciona nuevo turno

### Resultado esperado

- Turno anterior → CANCELADO

- Nuevo turno → CONFIRMADO

### Simulación

Usuario: Reprogramar turno\
Bot: Seleccioná nueva fecha

Usuario: 11/04\
Bot: Horarios disponibles:

- 11:00

Usuario: 11:00\
Bot: ✅ Turno reprogramado correctamente

### Resultado obtenido

✔ Turno anterior cancelado\
✔ Nuevo turno confirmado\
✔ Calendario actualizado

## Caso 5: Recordatorio automático

### Descripción

El sistema envía un recordatorio 24 horas antes.

### Pasos

1.  Scheduler detecta turno próximo

2.  Se envía mensaje al usuario

### Resultado esperado

- Usuario recibe recordatorio

- Puede confirmar o cancelar

### Simulación

Bot: 📅 Recordatorio de turno\
Tenés un turno mañana a las 10:00

¿Confirmás asistencia?

- SI

- CANCELAR

- REPROGRAMAR

### Resultado obtenido

✔ Mensaje enviado correctamente\
✔ Usuario puede interactuar

## Caso 6: Lista de espera

### Descripción

Un turno cancelado es ofrecido a otro paciente.

### Pasos

1.  Turno cancelado

2.  Sistema detecta lista de espera

3.  Se envía notificación

### Resultado esperado

- Primer usuario que acepta obtiene el turno

### Simulación

Bot: 📢 Se liberó un turno para hoy a las 10:00\
¿Querés tomarlo? (SI/NO)

Usuario: SI\
Bot: ✅ Turno asignado correctamente

### Resultado obtenido

✔ Turno asignado correctamente\
✔ Estado: CONFIRMADO

## **CAPÍTULO 6: Conclusiones y Trabajo Futuro**

El presente trabajo tuvo como objetivo el diseño e implementación de un
sistema automatizado de gestión de turnos médicos, orientado a
profesionales independientes, con el fin de optimizar la organización de
la agenda y reducir las ineficiencias asociadas a la gestión manual.

A partir del análisis realizado, se identificaron como principales
problemáticas la pérdida de turnos debido a inasistencias y la carga
operativa derivada de tareas administrativas repetitivas. En respuesta a
ello, se desarrolló una solución basada en la integración de
herramientas de mensajería, servicios de calendario y automatización de
procesos.

Los resultados obtenidos a través de los casos de prueba permiten
afirmar que el sistema cumple con los requerimientos definidos,
logrando:

> ● Automatizar el proceso completo de reserva, confirmación y gestión
> de turnos
>
> ● Reducir la intervención manual del profesional
>
> ● Mejorar la organización y aprovechamiento de la agenda

En particular, se destaca la implementación de mecanismos automáticos
que contribuyen directamente a la eficiencia del sistema. Por un lado,
el envío de recordatorios 24 horas antes del turno permite reducir la
probabilidad de inasistencia por olvido. Por otro lado, la gestión de
lista de espera ante cancelaciones o reprogramaciones posibilita la
reasignación de turnos liberados con antelación, evitando la pérdida de
disponibilidad en la agenda.

Estos dos procesos, actuando de forma conjunta, permiten maximizar la
utilización de los espacios disponibles, reduciendo el impacto económico
que generan los turnos no concretados.

Asimismo, el sistema presenta una arquitectura flexible y escalable, lo
que facilita su adaptación a otros contextos profesionales más allá del
ámbito médico.

En este sentido, el proyecto no solo cumple con los objetivos académicos
planteados, sino que también constituye una solución viable con
potencial de implementación en entornos reales.

### 6.2 Aportes del trabajo

El desarrollo realizado aporta:

> ● Un modelo automatizado de gestión de turnos basado en mensajería
> instantánea
>
> ● Un diseño de sistema escalable e integrable con servicios externos
>
> ● Un enfoque orientado a la optimización operativa y económica
>
> ● Una solución adaptable a distintos rubros profesionales

### 6.3 Limitaciones

Si bien el sistema desarrollado cumple con los objetivos planteados,
presenta ciertas limitaciones propias de un producto en etapa inicial:

> ● Implementación orientada a un único profesional
>
> ● Validación mediante casos de prueba y no en un entorno real con
> usuarios
>
> ● Dependencia de servicios externos (Telegram y Google Calendar)

Estas limitaciones no afectan la funcionalidad del sistema, pero
representan oportunidades de mejora a futuro.

### 6.4 Trabajo futuro

A partir del desarrollo realizado, se identifican diversas líneas de
evolución del sistema:

### **Escalabilidad**

> ● Adaptación para múltiples profesionales
>
> ● Implementación para consultorios o clínicas

### **Canales de comunicación**

> ● Integración con WhatsApp mediante API oficial
>
> ● Incorporación de nuevos canales de contacto

### **Funcionalidades avanzadas**

> ● Dashboard con métricas detalladas
>
> ● Análisis de asistencia y cancelaciones
>
> ● Reportes automatizados

### **Mejora en la interacción**

> ● Incorporación de procesamiento de lenguaje natural
>
> ● Flujos conversacionales más dinámicos

### **Seguridad**

> ● Implementación de autenticación avanzada
>
> ● Protección de datos sensibles
