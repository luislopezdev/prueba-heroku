// Función para formatear números con separadores de miles
function formatNumber(num) {
    return new Intl.NumberFormat('es-ES', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(num);
}

// Función para formatear BTC con 6 decimales
function formatBTC(num) {
    return new Intl.NumberFormat('es-ES', {
        minimumFractionDigits: 6,
        maximumFractionDigits: 6
    }).format(num);
}

// Función para encontrar el comerciante con mayor acumulado
function encontrarMaximo(datos, tipo) {
    let maximo = {
        nick: '',
        monto: 0
    };

    Object.entries(datos.estado).forEach(([merchant, info]) => {
        const monto = tipo === 'compra' ? info.usdt_acumulado_compra : info.usdt_acumulado_venta;
        if (monto > maximo.monto) {
            maximo = {
                nick: info.nick,
                monto: monto
            };
        }
    });

    return maximo;
}

// Función para crear una fila de datos
function crearFilaDatos(info, datos) {
    const row = document.createElement('tr');
    row.className = 'table-row-hover text-base';
    row.setAttribute('data-nick', info.nick);

    row.innerHTML = `
        <td class="text-left font-medium p-2">${info.nick}</td>
        <td class="text-center p-2">${info.compras_total}</td>
        <td class="text-center p-2 valor-positivo">$${formatNumber(info.btc_ultima_compra * datos.precio_btc)}</td>
        <td class="text-center p-2">${info.hora_ultima_compra}</td>
        <td class="text-center p-2 valor-positivo">$${formatNumber(info.usdt_acumulado_compra)}</td>
        <td class="text-center p-2">${info.ventas_total}</td>
        <td class="text-center p-2 valor-negativo">$${formatNumber(info.btc_ultima_venta * datos.precio_btc)}</td>
        <td class="text-center p-2">${info.hora_ultima_venta}</td>
        <td class="text-center p-2 valor-negativo">$${formatNumber(info.usdt_acumulado_venta)}</td>
    `;

    return row;
}

// Función para verificar usuarios repetidos
function verificarUsuariosRepetidos(datos) {
    const nicks = new Map();
    const repetidos = [];

    // Primero, agrupar todos los nicks
    Object.entries(datos.estado).forEach(([merchant, info]) => {
        const nick = info.nick.toLowerCase().trim(); // Normalizar el nick
        if (!nicks.has(nick)) {
            nicks.set(nick, [merchant]);
        } else {
            nicks.get(nick).push(merchant);
            if (!repetidos.includes(nick)) {
                repetidos.push(nick);
            }
        }
    });

    // Si hay repetidos, mostrar la alerta
    if (repetidos.length > 0) {
        console.log('Usuarios repetidos encontrados:', repetidos); // Debug

        const mensaje = repetidos.map(nick => {
            const merchants = nicks.get(nick);
            const infoCompleta = merchants.map(merchantId => {
                const info = datos.estado[merchantId];
                return `${merchantId} (${info.compras_total} compras, ${info.ventas_total} ventas)`;
            }).join('\n');
            return `El usuario "${nick}" aparece ${merchants.length} veces:\n${infoCompleta}`;
        }).join('\n\n');

        // Crear o actualizar la alerta
        let alerta = document.getElementById('alerta-repetidos');
        if (!alerta) {
            alerta = document.createElement('div');
            alerta.id = 'alerta-repetidos';
            alerta.className = 'fixed top-4 right-4 bg-red-500 text-white p-4 rounded-lg shadow-lg z-50 max-w-lg';
            document.body.appendChild(alerta);
        }

        // Actualizar contenido de la alerta
        alerta.innerHTML = `
            <div class="flex items-center justify-between mb-2">
                <div class="flex items-center gap-2">
                    <span class="text-xl">⚠️</span>
                    <h3 class="font-bold">Usuarios Repetidos Detectados</h3>
                </div>
                <button onclick="this.parentElement.parentElement.remove()" class="text-white hover:text-gray-200">
                    ✕
                </button>
            </div>
            <div class="text-sm whitespace-pre-line bg-red-600 p-2 rounded">${mensaje}</div>
        `;

        // Asegurar que la alerta sea visible
        alerta.style.display = 'block';
    } else {
        // Remover alerta si existe y no hay repetidos
        const alerta = document.getElementById('alerta-repetidos');
        if (alerta) {
            alerta.remove();
        }
    }
}

// Función para actualizar los datos en las tablas
function actualizarTabla(datos) {
    const tabla1 = document.getElementById('datos-tabla-1');
    const tabla2 = document.getElementById('datos-tabla-2');
    
    tabla1.innerHTML = '';
    tabla2.innerHTML = '';

    // Verificar usuarios repetidos
    verificarUsuariosRepetidos(datos);

    // Encontrar máximos acumulados
    const maxComprador = encontrarMaximo(datos, 'compra');
    const maxVendedor = encontrarMaximo(datos, 'venta');

    // Calcular totales
    let totalCompras = 0;
    let totalVentas = 0;
    const totalUsuarios = Object.keys(datos.estado).length;

    Object.values(datos.estado).forEach(info => {
        totalCompras += info.usdt_acumulado_compra;
        totalVentas += info.usdt_acumulado_venta;
    });

    // Actualizar información de máximos y totales
    document.getElementById('max-comprador').textContent = maxComprador.nick;
    document.getElementById('max-compra').textContent = formatNumber(maxComprador.monto);
    document.getElementById('max-vendedor').textContent = maxVendedor.nick;
    document.getElementById('max-venta').textContent = formatNumber(maxVendedor.monto);
    document.getElementById('total-compras').textContent = formatNumber(totalCompras);
    document.getElementById('total-ventas').textContent = formatNumber(totalVentas);
    document.getElementById('usuarios-monitoreados').textContent = totalUsuarios;

    // Convertir el objeto de estado en array y dividirlo en dos
    const merchants = Object.entries(datos.estado);
    const mitad = Math.ceil(merchants.length / 2);
    const primeraTabla = merchants.slice(0, mitad);
    const segundaTabla = merchants.slice(mitad);

    // Llenar primera tabla
    primeraTabla.forEach(([merchant, info]) => {
        const row = crearFilaDatos(info, datos);
        tabla1.appendChild(row);
    });

    // Llenar segunda tabla
    segundaTabla.forEach(([merchant, info]) => {
        const row = crearFilaDatos(info, datos);
        tabla2.appendChild(row);
    });

    // Actualizar información general
    document.getElementById('fecha-actual').textContent = datos.fecha_actual;
    document.getElementById('hora-actual').textContent = datos.hora_actual;
    document.getElementById('precio-btc').textContent = formatNumber(datos.precio_btc);
}

// Función para obtener datos del servidor
async function obtenerDatos() {
    try {
        const response = await fetch('/api/datos');
        const datos = await response.json();
        actualizarTabla(datos);
    } catch (error) {
        console.error('Error al obtener datos:', error);
    }
}

// Actualizar datos cada 10 segundos
setInterval(obtenerDatos, 10000);

// Cargar datos iniciales
obtenerDatos(); 