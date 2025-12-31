/****************************************************************************
**
** Copyright (C) 2021 The Qt Company Ltd.
** Contact: https://www.qt.io/licensing/
**
** This file is part of the QtWebChannel module of the Qt Toolkit.
**
** $QT_BEGIN_LICENSE:BSD$
** Commercial License Usage
** Licensees holding valid commercial Qt licenses may use this file in
** accordance with the commercial license agreement provided with the
** Software or, alternatively, in accordance with the terms contained in
** a written agreement between you and The Qt Company. For licensing terms
** and conditions see https://www.qt.io/terms-conditions. For further
** information use the contact form at https://www.qt.io/contact-us.
**
** BSD License Usage
** Alternatively, this file may be used under the terms of the BSD
** license as follows:
**
** "Redistribution and use in source and binary forms, with or without
** modification, are permitted provided that the following conditions are
** met:
** * Redistributions of source code must retain the above copyright
** notice, this list of conditions and the following disclaimer.
** * Redistributions in binary form must reproduce the above copyright
** notice, this list of conditions and the following disclaimer in
** the documentation and/or other materials provided with the
** distribution.
** * Neither the name of The Qt Company Ltd nor the names of its
** contributors may be used to endorse or promote products derived
** from this software without specific prior written permission.
**
**
** THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
** "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
** LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
** A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
** OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
** SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
** LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
** DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
** THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
** (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
** OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
**
** $QT_END_LICENSE$
**
****************************************************************************/
'use strict';

var QWebChannel = (function () {
    /**
     * @typedef {import('./qwebchannel.js').QWebChannelTransport} QWebChannelTransport
     * @typedef {import('./qwebchannel.js').QObject} QObject
     */

    /**
     * @typedef {object} QWebChannelMessage
     * @property {string} [object]
     * @property {number} [id]
     * @property {number} [type]
     * @property {number} [signal]
     * @property {string} [property]
     * @property {any[]} [args]
     * @property {any} [data]
     */

    /** The message types. @readonly */
    var QWebChannelMessageTypes = {
        signal: 1,
        propertyUpdate: 2,
        init: 3,
        response: 4,
        invokeMethod: 5
    };

    /**
     * Creates a QWebChannel that communicates with C++ over the given transport.
     *
     * The transport object is expected to have a `send` function and an `onmessage` callback.
     *
     * The `send` function takes a string as argument and is expected to send it to the C++ side.
     *
     * The `onmessage` callback is called when a message is received from the C++ side. It is
     * called with one argument, the message string.
     *
     * @param {QWebChannelTransport} transport The transport object.
     * @param {(channel: QWebChannel) => void} initCallback The callback to invoke when the
     * initialization is complete.
     */
    function QWebChannel(transport, initCallback) {
        if (typeof transport !== 'object' || typeof transport.send !== 'function') {
            console.error('The QWebChannel transport object is missing a "send" function.');
            return;
        }
        this.transport = transport;

        /** @type {Object<number, (data: any) => void>} */
        this.executes = {};
        this.execId = 0;
        /** @type {Object<string, QObject>} */
        this.objects = {};

        this.transport.onmessage =
            /** @param {MessageEvent<string>} message */
            function (message) {
                /** @type {QWebChannelMessage} */
                var data = JSON.parse(message.data);
                switch (data.type) {
                case QWebChannelMessageTypes.signal: {
                    var object = this.objects[data.object];
                    if (object) {
                        object.signalEmitted(data.signal, data.args);
                    } else {
                        console.warn('Received signal for unknown object ' + data.object);
                    }
                } break;
                case QWebChannelMessageTypes.response: {
                    var execute = this.executes[data.id];
                    if (execute) {
                        execute(data.data);
                        delete this.executes[data.id];
                    } else {
                        console.warn('Received response for unknown id ' + data.id);
                    }
                } break;
                case QWebChannelMessageTypes.propertyUpdate: {
                    for (var i in data.data) {
                        var object = this.objects[i];
                        if (object) {
                            object.propertyUpdate(data.data[i]);
                        } else {
                            console.warn('Received property update for unknown object ' + i);
                        }
                    }
                } break;
                default:
                    console.error('Invalid message received:', message.data);
                    break;
                }
            }.bind(this);

        this.initCallback = initCallback;

        this.send({ type: QWebChannelMessageTypes.init });
    }

    /**
     * @param {QWebChannelMessage} message The message to send.
     * @private
     */
    QWebChannel.prototype.send = function (message) {
        this.transport.send(JSON.stringify(message));
    };

    /**
     * @param {string} objectName The name of the object.
     * @param {string} methodName The name of the method.
     * @param {any[]} args The arguments of the method.
     * @param {(data: any) => void} [callback] The callback to invoke with the return value.
     * @private
     */
    QWebChannel.prototype.invokeMethod = function (objectName, methodName, args, callback) {
        var id = ++this.execId;
        if (callback) {
            this.executes[id] = callback;
        }
        this.send({
            type: QWebChannelMessageTypes.invokeMethod,
            id: id,
            object: objectName,
            method: methodName,
            args: args
        });
    };

    /**
     * @param {string} objectName The name of the object.
     * @param {string} propertyName The name of the property.
     * @param {any} value The new value of the property.
     * @private
     */
    QWebChannel.prototype.setProperty = function (objectName, propertyName, value) {
        this.send({
            type: QWebChannelMessageTypes.propertyUpdate,
            object: objectName,
            property: propertyName,
            value: value
        });
    };

    /**
     * @param {any} data The data received from C++.
     * @private
     */
    QWebChannel.prototype.receive = function (data) {
        if (typeof data === 'string') {
            data = JSON.parse(data);
        }
        /** @type {Object<string, QObject>} */
        var objects = {};
        for (var objectName in data) {
            var object = new QObject(objectName, data[objectName], this);
            this.objects[objectName] = object;
            objects[objectName] = object;
        }
        if (this.initCallback) {
            this.initCallback(this);
        }
    };

    /**
     * A QObject representation in JavaScript.
     *
     * The meta-object information of the C++ QObject is exposed to JavaScript. All of its
     * properties, signals and slots are available.
     *
     * Properties can be accessed and set as usual.
     *
     * Signals can be connected to a JavaScript function.
     *
     * Slots can be called as methods.
     *
     * Example:
     *
     * ```javascript
     * // C++:
     * // MyObject *obj = new MyObject(this);
     * // channel->registerObject("myobj", obj);
     *
     * // JavaScript:
     * // new QWebChannel(transport, function(channel) {
     * //   var myobj = channel.objects.myobj;
     * //   myobj.someProperty = "new value";
     * //   myobj.someSignal.connect(function(newValue) {
     * //     console.log("someProperty changed to " + newValue);
     * //   });
     * //   myobj.someSlot(1, 2, 3);
     * // });
     * ```
     *
     * @param {string} name The name of the C++ QObject.
     * @param {any} data The meta-object information of the C++ QObject.
     * @param {QWebChannel} webChannel The QWebChannel this object belongs to.
     */
    function QObject(name, data, webChannel) {
        this.__id__ = name;
        this.webChannel = webChannel;

        /** @type {Object<string, {
         * connect: (callback: (...args: any[]) => void) => void,
         * disconnect: (callback: (...args: any[]) => void) => void
         * }>} The signals of this object.
         */
        this.signals = {};
        /** @private */
        this.signalHandlers = {};

        var object = this;

        for (var i in data.methods) {
            var method = data.methods[i];
            object[method[0]] = (function (methodName, methodIdx) {
                return function () {
                    var args = [];
                    var callback;
                    for (var i = 0; i < arguments.length; ++i) {
                        if (typeof arguments[i] === 'function') {
                            callback = arguments[i];
                        } else {
                            args.push(arguments[i]);
                        }
                    }
                    object.webChannel.invokeMethod(object.__id__, methodIdx, args, callback);
                };
            })(method[0], method[1]);
        }

        for (var i in data.properties) {
            var property = data.properties[i];
            Object.defineProperty(object, property[0], {
                configurable: true,
                get: function () {
                    return object['__' + this.name];
                }.bind({ name: property[0] }),
                set: function (value) {
                    object.webChannel.setProperty(object.__id__, this.name, value);
                }.bind({ name: property[0] })
            });
            this['__' + property[0]] = property[1];
        }

        for (var i in data.signals) {
            var signal = data.signals[i];
            object.signals[signal[0]] = (function (signalName, signalIdx) {
                return {
                    connect: function (callback) {
                        if (typeof callback !== 'function') {
                            console.error('Signal ' + signalName + ' expects a function as argument.');
                            return;
                        }
                        var handlers = object.signalHandlers[signalIdx];
                        if (handlers === undefined) {
                            handlers = [];
                            object.signalHandlers[signalIdx] = handlers;
                        }
                        handlers.push(callback);
                    },
                    disconnect: function (callback) {
                        if (typeof callback !== 'function') {
                            console.error('Signal ' + signalName + ' expects a function as argument.');
                            return;
                        }
                        var handlers = object.signalHandlers[signalIdx];
                        if (handlers === undefined) {
                            return;
                        }
                        var i = handlers.indexOf(callback);
                        if (i !== -1) {
                            handlers.splice(i, 1);
                        }
                    }
                };
            })(signal[0], signal[1]);
        }
    }

    /**
     * @param {Object<string, any>} propertyMap The map of properties to update.
     * @private
     */
    QObject.prototype.propertyUpdate = function (propertyMap) {
        for (var propertyName in propertyMap) {
            this['__' + propertyName] = propertyMap[propertyName];
            var handlers = this.signalHandlers[propertyName + 'Changed'];
            if (handlers) {
                var args = [];
                args.push(propertyMap[propertyName]);
                handlers.forEach(function (handler) {
                    handler.apply(null, args);
                });
            }
        }
    };

    /**
     * @param {number} signalIdx The index of the signal.
     * @param {any[]} signalArgs The arguments of the signal.
     * @private
     */
    QObject.prototype.signalEmitted = function (signalIdx, signalArgs) {
        var handlers = this.signalHandlers[signalIdx];
        if (handlers) {
            handlers.forEach(function (handler) {
                handler.apply(null, signalArgs);
            });
        }
    };

    return QWebChannel;
}());