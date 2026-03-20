#include <wiringPi.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <unistd.h>

#define DHTPIN 20  // 可对应 wiringOP GPIO 编号

// 读取 DHT11 函数
int readDHT11(int *temperature, int *humidity) {
    uint8_t data[5] = {0,0,0,0,0};
    int bitidx = 0;

    pinMode(DHTPIN, OUTPUT);
    digitalWrite(DHTPIN, LOW);
    delay(18);              
    digitalWrite(DHTPIN, HIGH);
    delayMicroseconds(40);
    pinMode(DHTPIN, INPUT);

    while(digitalRead(DHTPIN) == HIGH);
    while(digitalRead(DHTPIN) == LOW);
    while(digitalRead(DHTPIN) == HIGH);

    for (int i = 0; i < 40; i++) {
        while(digitalRead(DHTPIN) == LOW);
        long t = micros();
        while(digitalRead(DHTPIN) == HIGH);
        long dt = micros() - t;

        data[bitidx/8] <<= 1;
        if(dt > 50) data[bitidx/8] |= 1;
        bitidx++;
    }

    if ((uint8_t)(data[0]+data[1]+data[2]+data[3]) != data[4]) return 1; // 错误

    *humidity = data[0];
    *temperature = data[2];
    return 0;
}

int main() {
    if (wiringPiSetup() == -1) {
        printf("GPIO 初始化失败\n");
        return 1;
    }

    while (1) {
        int temp, hum;
        if(readDHT11(&temp, &hum) == 0){
            printf("温度: %d°C, 湿度: %d%%\n", temp, hum);
            fflush(stdout); // 刷新输出缓冲区
        }
        else
            printf("读取失败\n");

        sleep(2); // DHT11 最小读取间隔 1 秒，保险起见给2s，之前给1.2s也堵塞了
    }

    return 0;
}