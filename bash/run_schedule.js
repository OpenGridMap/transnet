"use strict";

const exec = require('child_process').exec;

const interval = setInterval(checkDate, 60000);

function checkDate() {
    const currentDate = new Date();
    if (currentDate.getDay() === 2 && currentDate.getHours() === 11 && currentDate.getMinutes() === 30) {
        console.log('Started Running the Script!');
        console.log(currentDate);
        runScript();
    }
}

function runScript() {
    let script = exec('sh run_planet.sh',
        (error, stdout, stderr) => {
            console.log(`${stdout}`);
            console.log(`${stderr}`);
            if (error !== null) {
                console.log(`exec error: ${error}`);
            }
        });
}
